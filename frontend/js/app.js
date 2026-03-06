const API_BASE = '/api';

// Logging Utility
const logger = {
    debug: (...args) => console.debug('[DEBUG]', new Date().toISOString(), ...args),
    info: (...args) => console.info('[INFO]', new Date().toISOString(), ...args),
    warn: (...args) => console.warn('[WARN]', new Date().toISOString(), ...args),
    error: (...args) => console.error('[ERROR]', new Date().toISOString(), ...args)
};

// State
let userData = null;
let dashboardData = null;
let showAmount = false;

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
});

async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/user/me`, { credentials: 'include' });
        if (res.status === 401 || res.status === 403 || res.status === 404) {
            const errorBody = await res.text();
            logger.info(`User access issue (status ${res.status}): ${errorBody}, showing login`);
            showLogin();
            return;
        }

        if (!res.ok) {
            const errorText = await res.text();
            throw new Error(`Failed to fetch user (status ${res.status}): ${errorText}`);
        }

        userData = await res.json();
        logger.debug("User data loaded", userData);

        if (userData.MemberId && !userData.IsApproved) {
            showPendingStatus();
        } else if (!userData.IsBound) {
            showBindModal();
        } else {
            showDashboard();
            loadDashboard();
        }

    } catch (e) {
        logger.error("checkAuth error", e);
        showLogin();
    }
}

function showLogin() {
    document.getElementById('login-view').classList.remove('hidden');
    document.getElementById('dashboard-view').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('dashboard-view').classList.remove('hidden');

    document.getElementById('user-name').textContent = userData.LineName || userData.MemberName;
    document.getElementById('user-id').textContent = `ID: ${userData.MemberId}`;
}

function showBindModal() {
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('dashboard-view').classList.remove('hidden');
    document.getElementById('bind-modal').classList.remove('hidden');
}

function showPendingStatus() {
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('dashboard-view').classList.remove('hidden');

    // Replace modal content with pending message
    const modalContent = document.querySelector('#bind-modal .bg-white');
    if (modalContent) {
        modalContent.innerHTML = `
            <div class="p-8 text-center">
                <div class="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <h3 class="text-xl font-bold text-gray-900 mb-2">綁定申請中</h3>
                <p class="text-gray-500">您的申請已送出，請靜待管理員審核通過。</p>
                <p class="text-sm text-gray-400 mt-4">申請日期：${userData.ApplyDate ? new Date(userData.ApplyDate).toLocaleDateString() : '今日'}</p>
                <button onclick="location.reload()" class="mt-6 w-full py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">重新整理</button>
            </div>
        `;
    }
    document.getElementById('bind-modal').classList.remove('hidden');
}

async function submitBind() {
    const name = document.getElementById('bind-name').value;
    const id = document.getElementById('bind-id').value;

    if (!name || !id) {
        alert("請輸入完整資訊");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/user/bind`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                member_id: id,
                member_name: name,
                line_id: userData.LineId, // Redundant but per schema
                line_name: userData.LineName || name
            })
        });

        if (!res.ok) {
            const err = await res.json();
            logger.warn("Binding failed", err);
            alert(err.detail || "綁定失敗");
            return;
        }

        const data = await res.json();
        logger.info("Binding response", data);

        if (data.status === 'pending') {
            alert(data.message || "綁定申請中");
        } else {
            logger.info("Binding successful");
        }

        document.getElementById('bind-modal').classList.add('hidden');
        location.reload();

    } catch (e) {
        alert("綁定發生錯誤");
    }
}

async function loadDashboard() {
    try {
        const res = await fetch(`${API_BASE}/user/dashboard`, { credentials: 'include' });
        if (!res.ok) throw new Error("Failed to load dashboard");

        dashboardData = await res.json();
        renderDashboard();
    } catch (e) {
        logger.error("loadDashboard error", e);
    }
}

function renderDashboard() {
    // Amounts
    const amtEl = document.getElementById('total-amount');
    amtEl.dataset.value = dashboardData.total_amount.toLocaleString();
    amtEl.textContent = showAmount ? amtEl.dataset.value : '****';

    document.getElementById('total-count').textContent = dashboardData.total_count;

    // List grouping by month
    const listEl = document.getElementById('devotion-list');
    const groups = {};
    dashboardData.recent_devotions.forEach(d => {
        const date = new Date(d.DevotionDate);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        if (!groups[monthKey]) {
            groups[monthKey] = {
                label: `${date.getFullYear()}年${date.getMonth() + 1}月`,
                total: 0,
                items: []
            };
        }
        groups[monthKey].total += d.Amount;
        groups[monthKey].items.push(d);
    });

    const sortedMonthKeys = Object.keys(groups).sort().reverse();

    listEl.innerHTML = sortedMonthKeys.map(monthKey => {
        const group = groups[monthKey];
        const detailRows = group.items.map(d => `
            <tr class="month-details-${monthKey} hidden bg-gray-50/50">
                <td class="px-6 py-3 whitespace-nowrap text-xs text-gray-500 pl-12">${new Date(d.DevotionDate).toLocaleDateString()}</td>
                <td class="px-6 py-3 whitespace-nowrap text-xs text-gray-900">${d.CategoryName || d.CategoryId}</td>
                <td class="px-6 py-3 whitespace-nowrap text-xs text-gray-500 text-right">${d.Amount.toLocaleString()}</td>
            </tr>
        `).join('');

        return `
            <tr onclick="toggleMonth('${monthKey}')" class="cursor-pointer hover:bg-indigo-50 transition-colors bg-white">
                <td colspan="2" class="px-6 py-4 whitespace-nowrap text-sm font-bold text-indigo-600 flex items-center">
                    <svg id="chevron-${monthKey}" class="w-4 h-4 mr-2 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                    ${group.label}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-indigo-600 text-right">
                    ${group.total.toLocaleString()}
                </td>
            </tr>
            ${detailRows}
        `;
    }).join('');

    // Charts
    renderCharts();
}

function toggleMonth(monthKey) {
    const details = document.querySelectorAll(`.month-details-${monthKey}`);
    const chevron = document.getElementById(`chevron-${monthKey}`);

    details.forEach(el => {
        el.classList.toggle('hidden');
    });

    if (chevron) {
        chevron.classList.toggle('rotate-90');
    }
}

function toggleAmount() {
    showAmount = !showAmount;
    const amtEl = document.getElementById('total-amount');
    if (amtEl.dataset.value) {
        amtEl.textContent = showAmount ? amtEl.dataset.value : '****';
    }
}

function renderCharts() {
    // Donut
    const ctxDonut = document.getElementById('categoryChart').getContext('2d');
    const catLabels = Object.keys(dashboardData.category_distribution);
    const catValues = Object.values(dashboardData.category_distribution);

    new Chart(ctxDonut, {
        type: 'doughnut',
        data: {
            labels: catLabels,
            datasets: [{
                data: catValues,
                backgroundColor: [
                    '#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'
                ]
            }]
        },
        options: {
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.label || '';
                            if (label) {
                                label += ': ';
                            }
                            const val = context.raw;
                            const total = context.chart._metasets[context.datasetIndex].total;
                            const pct = ((val / total) * 100).toFixed(1) + '%';
                            label += val.toLocaleString() + ' (' + pct + ')';
                            return label;
                        }
                    }
                }
            }
        }
    });

    // Stacked Bar (Simplified to single bar for history or group by month?)
    // Spec says: "Stacked Bar ... by category ... by date"
    // For MVP, lets just do bar chart of amounts by date
    // Or simpler history.
    // Assuming 'recent_devotions' has date.

    // Group by Date
    const dateMap = {};
    dashboardData.recent_devotions.forEach(d => {
        const date = new Date(d.DevotionDate).toLocaleDateString();
        dateMap[date] = (dateMap[date] || 0) + d.Amount;
    });

    // const sortedDates = Object.keys(dateMap).sort(); // Basic sort
    const sortedDates = Object.keys(dateMap).sort((a, b) => {
        return new Date(a) - new Date(b);
    });

    const ctxBar = document.getElementById('historyChart').getContext('2d');
    new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: sortedDates,
            datasets: [{
                label: '每日奉獻',
                data: sortedDates.map(d => dateMap[d]),
                backgroundColor: '#6366F1'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function logout() {
    window.location.href = '/api/auth/logout';
}
