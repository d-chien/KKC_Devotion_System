import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.member_import import (
    analyze_members,
    apply_resolutions,
    mask_name,
    name_hash,
    MemberImportError,
    UnresolvedConflictsError,
)


def row(member_id, name):
    return {'member_id': member_id, 'name': name}


def member(member_id, real_name, is_bind=False, hashed=True, bind_date=None):
    return {
        'member_id': member_id,
        'masked_name': mask_name(real_name),
        'name_hash': name_hash(real_name) if hashed else None,
        'is_bind': is_bind,
        'bind_date': bind_date,
    }


class TestAnalyzeMembers(unittest.TestCase):
    def test_duplicate_member_ids_in_file_rejected(self):
        with self.assertRaises(MemberImportError) as ctx:
            analyze_members([row('1', '王大明'), row('1', '李小華')], [])
        self.assertIn('1', str(ctx.exception))

    def test_empty_fields_rejected(self):
        with self.assertRaises(MemberImportError):
            analyze_members([row('', '王大明')], [])
        with self.assertRaises(MemberImportError):
            analyze_members([row('1', '')], [])

    def test_exact_hash_match_updates_number(self):
        existing = [member('A01', '王大明', is_bind=True)]
        plan = analyze_members([row('B99', '王大明')], existing)
        self.assertEqual(plan['updates'], [{
            'old_id': 'A01', 'new_id': 'B99', 'name': '王大明',
            'masked_name': '王O明', 'is_bind': True,
        }])
        self.assertEqual(plan['creates'], [])
        self.assertEqual(plan['conflicts'], [])
        self.assertEqual(plan['deletes'], [])

    def test_hash_distinguishes_names_with_same_mask(self):
        # 王大明 / 王小明 both mask to 王O明 but hashes differ → no conflict
        existing = [member('A01', '王大明'), member('A02', '王小明')]
        plan = analyze_members([row('B01', '王大明'), row('B02', '王小明')], existing)
        self.assertEqual(len(plan['updates']), 2)
        self.assertEqual(plan['conflicts'], [])

    def test_new_name_creates_and_absent_member_deleted(self):
        existing = [member('A01', '王大明', is_bind=True)]
        plan = analyze_members([row('B01', '陳新人')], existing)
        self.assertEqual(plan['updates'], [])
        self.assertEqual(plan['creates'][0]['new_id'], 'B01')
        self.assertEqual(plan['deletes'], [{
            'member_id': 'A01', 'masked_name': '王O明', 'is_bind': True,
        }])

    def test_same_name_multiple_existing_is_conflict(self):
        existing = [member('A01', '王大明'), member('A02', '王大明', is_bind=True)]
        plan = analyze_members([row('B01', '王大明')], existing)
        self.assertEqual(plan['updates'], [])
        self.assertEqual(len(plan['conflicts']), 1)
        cand_ids = {c['member_id'] for c in plan['conflicts'][0]['candidates']}
        self.assertEqual(cand_ids, {'A01', 'A02'})
        # candidates are "maybe kept" → not listed as deletes yet
        self.assertEqual(plan['deletes'], [])

    def test_same_name_multiple_file_rows_is_conflict(self):
        existing = [member('A01', '王大明')]
        plan = analyze_members([row('B01', '王大明'), row('B02', '王大明')], existing)
        self.assertEqual(plan['updates'], [])
        self.assertEqual(len(plan['conflicts']), 2)

    def test_legacy_masked_fallback_matches(self):
        # Pre-NameHash doc: only the masked name is known
        existing = [member('A01', '王大明', hashed=False)]
        plan = analyze_members([row('B01', '王大明')], existing)
        self.assertEqual(plan['updates'][0]['old_id'], 'A01')

    def test_legacy_masked_fallback_double_claim_escalates_to_conflict(self):
        # Two different real names mask identically and both hit one legacy doc
        existing = [member('A01', '王大明', hashed=False)]
        plan = analyze_members([row('B01', '王大明'), row('B02', '王小明')], existing)
        self.assertEqual(plan['updates'], [])
        self.assertEqual(len(plan['conflicts']), 2)

    def test_unchanged_number_is_still_an_update(self):
        existing = [member('A01', '王大明')]
        plan = analyze_members([row('A01', '王大明')], existing)
        self.assertEqual(plan['updates'][0]['old_id'], 'A01')
        self.assertEqual(plan['updates'][0]['new_id'], 'A01')


class TestApplyResolutions(unittest.TestCase):
    def setUp(self):
        self.existing = [member('A01', '王大明'), member('A02', '王大明', is_bind=True)]
        self.plan = analyze_members([row('B01', '王大明')], self.existing)

    def test_unresolved_conflict_raises(self):
        with self.assertRaises(UnresolvedConflictsError):
            apply_resolutions(self.plan, {}, self.existing)

    def test_match_resolution_updates_and_deletes_unchosen(self):
        final = apply_resolutions(
            self.plan, {'B01': {'action': 'match', 'old_id': 'A02'}}, self.existing)
        self.assertEqual(final['updates'][0]['old_id'], 'A02')
        self.assertTrue(final['updates'][0]['is_bind'])
        deleted_ids = {d['member_id'] for d in final['deletes']}
        self.assertEqual(deleted_ids, {'A01'})

    def test_create_resolution_deletes_all_candidates(self):
        final = apply_resolutions(
            self.plan, {'B01': {'action': 'create'}}, self.existing)
        self.assertEqual({c['new_id'] for c in final['creates']}, {'B01'})
        deleted_ids = {d['member_id'] for d in final['deletes']}
        self.assertEqual(deleted_ids, {'A01', 'A02'})

    def test_resolution_outside_candidates_rejected(self):
        with self.assertRaises(MemberImportError):
            apply_resolutions(
                self.plan, {'B01': {'action': 'match', 'old_id': 'ZZZ'}}, self.existing)

    def test_two_rows_cannot_claim_same_member(self):
        existing = [member('A01', '王大明')]
        plan = analyze_members([row('B01', '王大明'), row('B02', '王大明')], existing)
        with self.assertRaises(MemberImportError):
            apply_resolutions(plan, {
                'B01': {'action': 'match', 'old_id': 'A01'},
                'B02': {'action': 'match', 'old_id': 'A01'},
            }, existing)

    def test_number_swap_mapping(self):
        existing = [member('1', '王大明', is_bind=True), member('2', '李小華')]
        plan = analyze_members([row('2', '王大明'), row('1', '李小華')], existing)
        final = apply_resolutions(plan, {}, existing)
        mapping = {u['old_id']: u['new_id'] for u in final['updates']}
        self.assertEqual(mapping, {'1': '2', '2': '1'})
        self.assertEqual(final['deletes'], [])


class TestAnalyzeEndpoint(unittest.TestCase):
    """Smoke test of the /api/admin/upload/members/analyze response shape."""

    @classmethod
    def setUpClass(cls):
        from unittest.mock import MagicMock
        # Mock Firebase/Firestore BEFORE importing backend modules
        for mod in ("firebase_admin", "firebase_admin.credentials",
                    "firebase_admin.firestore", "google.cloud",
                    "google.cloud.firestore"):
            sys.modules.setdefault(mod, MagicMock())

        from fastapi.testclient import TestClient
        from backend.main import app
        from backend.api import deps

        app.dependency_overrides[deps.get_current_admin] = lambda: {"Role": "Admin"}
        cls.app = app
        cls.deps = deps
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.app.dependency_overrides.pop(cls.deps.get_current_admin, None)

    def _post_csv(self, csv_bytes, existing_docs):
        from unittest.mock import MagicMock, patch

        docs = []
        for m in existing_docs:
            doc = MagicMock()
            doc.id = m['member_id']
            doc.to_dict.return_value = {
                'Name': m['masked_name'],
                'NameHash': m.get('name_hash'),
                'isBind': m.get('is_bind', False),
                'BindDate': m.get('bind_date'),
            }
            docs.append(doc)
        fake_db = MagicMock()
        fake_db.collection.return_value.stream.return_value = iter(docs)

        with patch('backend.api.admin.get_db', return_value=fake_db):
            return self.client.post(
                '/api/admin/upload/members/analyze',
                files={'file': ('members.csv', csv_bytes, 'text/csv')},
            )

    def test_preview_shape(self):
        existing = [member('A01', '王大明', is_bind=True)]
        res = self._post_csv('MemberId,Name\nB99,王大明\nC01,陳新人\n'.encode('utf-8'), existing)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'preview')
        self.assertEqual(data['renumbered_count'], 1)
        self.assertEqual(data['updates'][0]['old_id'], 'A01')
        self.assertEqual(data['updates'][0]['new_id'], 'B99')
        self.assertEqual(len(data['creates']), 1)
        self.assertEqual(data['conflicts'], [])
        self.assertEqual(data['bound_deletes'], [])

    def test_duplicate_ids_in_file_400(self):
        res = self._post_csv('MemberId,Name\n1,王大明\n1,李小華\n'.encode('utf-8'), [])
        self.assertEqual(res.status_code, 400)
        self.assertIn('重複', res.json()['detail'])


if __name__ == '__main__':
    unittest.main()
