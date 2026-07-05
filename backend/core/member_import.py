"""Pure matching/validation logic for the member list upload.

Firestore-free so it can be unit-tested directly. The member number is the
Members document ID; identity across uploads is carried by the person's name
(exact match via NameHash, with a masked-name fallback for documents created
before NameHash existed).
"""
import hashlib
import unicodedata


class MemberImportError(Exception):
    """Fatal problem with the uploaded file (bad rows, duplicate ids...)."""


class UnresolvedConflictsError(Exception):
    """Same-name conflicts exist that require admin confirmation."""


def name_hash(name: str) -> str:
    normalized = unicodedata.normalize('NFC', name.strip())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def mask_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return name
    name = name.strip()
    if len(name) == 2:
        return name[0] + "O"
    elif len(name) >= 3:
        return name[0] + "O" * (len(name) - 2) + name[-1]
    return name


def analyze_members(file_rows, existing_members):
    """Classify uploaded rows against existing members.

    file_rows: [{'member_id': str, 'name': str}] (already stripped)
    existing_members: [{'member_id', 'masked_name', 'name_hash' (or None),
                        'is_bind', 'bind_date'}]

    Returns a plan dict:
      updates:   [{'old_id', 'new_id', 'name', 'masked_name', 'is_bind'}]
      creates:   [{'new_id', 'name', 'masked_name'}]
      conflicts: [{'new_id', 'name', 'masked_name',
                   'candidates': [{'member_id', 'masked_name', 'is_bind'}]}]
      deletes:   [{'member_id', 'masked_name', 'is_bind'}]

    Raises MemberImportError for empty fields or duplicate MemberIds in the
    file (the post-update "no duplicate numbers" guarantee).
    """
    # --- File-level validation ---
    bad_rows = [i + 1 for i, r in enumerate(file_rows)
                if not r.get('member_id') or not r.get('name')]
    if bad_rows:
        raise MemberImportError(f"檔案第 {bad_rows} 列缺少 MemberId 或 Name")

    seen, dup_ids = set(), set()
    for r in file_rows:
        mid = r['member_id']
        (dup_ids if mid in seen else seen).add(mid)
    if dup_ids:
        raise MemberImportError(f"檔案內會友編號重複：{sorted(dup_ids)}")

    # --- Build match indexes over existing members ---
    by_hash = {}
    by_masked_legacy = {}  # only docs without NameHash
    for m in existing_members:
        if m.get('name_hash'):
            by_hash.setdefault(m['name_hash'], []).append(m)
        else:
            by_masked_legacy.setdefault(m.get('masked_name'), []).append(m)

    name_counts = {}
    for r in file_rows:
        h = name_hash(r['name'])
        name_counts[h] = name_counts.get(h, 0) + 1

    def _candidates(name):
        exact = by_hash.get(name_hash(name), [])
        if exact:
            return exact
        return by_masked_legacy.get(mask_name(name), [])

    def _public(m):
        return {'member_id': m['member_id'], 'masked_name': m.get('masked_name'),
                'is_bind': bool(m.get('is_bind'))}

    # --- First pass: classify each row ---
    updates, creates, conflicts = [], [], []
    for r in file_rows:
        cands = _candidates(r['name'])
        masked = mask_name(r['name'])
        entry = {'new_id': r['member_id'], 'name': r['name'], 'masked_name': masked}
        if not cands:
            creates.append(entry)
        elif len(cands) > 1 or name_counts[name_hash(r['name'])] > 1:
            conflicts.append({**entry, 'candidates': [_public(m) for m in cands]})
        else:
            m = cands[0]
            updates.append({'old_id': m['member_id'], 'new_id': r['member_id'],
                            'name': r['name'], 'masked_name': masked,
                            'is_bind': bool(m.get('is_bind'))})

    # --- Escalate: one existing member auto-claimed by several rows
    # (possible via the lossy masked-name fallback) ---
    claims = {}
    for u in updates:
        claims.setdefault(u['old_id'], []).append(u)
    contested = {old for old, us in claims.items() if len(us) > 1}
    if contested:
        remaining = []
        for u in updates:
            if u['old_id'] in contested:
                cands = _candidates(u['name'])
                conflicts.append({'new_id': u['new_id'], 'name': u['name'],
                                  'masked_name': u['masked_name'],
                                  'candidates': [_public(m) for m in cands]})
            else:
                remaining.append(u)
        updates = remaining

    # --- Deletes: existing members not matched and not a conflict candidate ---
    matched = {u['old_id'] for u in updates}
    maybe_kept = {c['member_id'] for cf in conflicts for c in cf['candidates']}
    deletes = [_public(m) for m in existing_members
               if m['member_id'] not in matched and m['member_id'] not in maybe_kept]

    return {'updates': updates, 'creates': creates,
            'conflicts': conflicts, 'deletes': deletes}


def apply_resolutions(plan, resolutions, existing_members):
    """Fold admin decisions for conflicts into the plan.

    resolutions: {new_id: {'action': 'match', 'old_id': ...}
                          | {'action': 'create'}}

    Returns a final plan {'updates', 'creates', 'deletes'} with deletes
    recomputed. Raises UnresolvedConflictsError if any conflict has no
    resolution, MemberImportError for invalid ones.
    """
    resolutions = resolutions or {}
    updates = list(plan['updates'])
    creates = list(plan['creates'])

    unresolved = []
    for cf in plan['conflicts']:
        res = resolutions.get(cf['new_id'])
        if not res or res.get('action') not in ('match', 'create'):
            unresolved.append(cf)
            continue
        if res['action'] == 'create':
            creates.append({'new_id': cf['new_id'], 'name': cf['name'],
                            'masked_name': cf['masked_name']})
        else:
            old_id = res.get('old_id')
            cand = next((c for c in cf['candidates'] if c['member_id'] == old_id), None)
            if cand is None:
                raise MemberImportError(
                    f"編號 {cf['new_id']} 的確認選項無效：{old_id} 不在候選名單中")
            updates.append({'old_id': old_id, 'new_id': cf['new_id'],
                            'name': cf['name'], 'masked_name': cf['masked_name'],
                            'is_bind': cand['is_bind']})
    if unresolved:
        raise UnresolvedConflictsError(unresolved)

    # No existing member may be claimed by two rows.
    claims = {}
    for u in updates:
        claims.setdefault(u['old_id'], []).append(u['new_id'])
    dup_claims = {old: news for old, news in claims.items() if len(news) > 1}
    if dup_claims:
        raise MemberImportError(f"同一位既有會友被多列選為更新對象：{dup_claims}")

    matched = set(claims)
    deletes = [{'member_id': m['member_id'], 'masked_name': m.get('masked_name'),
                'is_bind': bool(m.get('is_bind'))}
               for m in existing_members if m['member_id'] not in matched]

    return {'updates': updates, 'creates': creates, 'deletes': deletes}
