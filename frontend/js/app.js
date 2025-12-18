const API_BASE = '/api';

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
        if (res.status === 401 || res.status === 403) {
            showLogin();
            return;
        }

        if (!res.ok) throw new Error("Failed to fetch user");

        userData = await res.json();

        if (!userData.IsBound) {
            showBindModal();
        } else {
            showDashboard();
            loadDashboard();
        }

    } catch (e) {
        console.error(e);
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
    // Show Dashboard background but with Modal
    // But actually simpler to just show modal
    document.getElementById('login-view').classList.add('hidden');
    document.getElementById('dashboard-view').classList.remove('hidden'); // Navbar visible
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
            alert(err.detail || "綁定失敗");
            return;
        }

        document.getElementById('bind-modal').classList.add('hidden');
        // Reload or update state
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
        console.error(e);
    }
}

function renderDashboard() {
    // Amounts
    const amtEl = document.getElementById('total-amount');
    amtEl.dataset.value = dashboardData.total_amount.toLocaleString();
    amtEl.textContent = showAmount ? amtEl.dataset.value : '****';

    document.getElementById('total-count').textContent = dashboardData.total_count;

    // List
    const listEl = document.getElementById('devotion-list');
    listEl.innerHTML = dashboardData.recent_devotions.map(d => `
        <tr>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${new Date(d.DevotionDate).toLocaleDateString()}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${d.CategoryName || d.CategoryId}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">${d.Amount.toLocaleString()}</td>
        </tr>
    `).join('');

    // Charts
    renderCharts();
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

    const sortedDates = Object.keys(dateMap).sort(); // Basic sort

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
        }
    });
}

function logout() {
    window.location.href = '/api/auth/logout';
}
