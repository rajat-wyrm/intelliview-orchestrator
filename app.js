/* =============================================================================
   AI Response Quality Dashboard — Application Logic
   ============================================================================= */

// ── State ────────────────────────────────────────────────────────────────────
const state = {
    currentPage: 1,
    pageSize: 15,
    sortBy: 'timestamp',
    sortOrder: 'desc',
    filters: {},
    charts: {},
};

// ── API Helpers ──────────────────────────────────────────────────────────────
const API_BASE = '';

async function fetchJSON(url) {
    const res = await fetch(API_BASE + url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function postJSON(url, body) {
    const res = await fetch(API_BASE + url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    refreshAll();
});

async function refreshAll() {
    document.getElementById('lastRefresh').textContent =
        'Last updated: ' + new Date().toLocaleTimeString();
    await Promise.all([loadStats(), loadLogs()]);
}

// ── Stats & KPI ──────────────────────────────────────────────────────────────
async function loadStats() {
    try {
        const stats = await fetchJSON('/api/stats');
        renderKPIs(stats);
        renderCharts(stats);
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

function renderKPIs(stats) {
    document.getElementById('kpiTotal').textContent =
        stats.total_evaluations.toLocaleString();
    document.getElementById('kpiAvgScore').textContent =
        stats.avg_score.toFixed(1);
    document.getElementById('kpiAvgConf').textContent =
        (stats.avg_confidence * 100).toFixed(0) + '%';

    const llm = stats.method_breakdown.llm || 0;
    const rb = stats.method_breakdown.rule_based || 0;
    const total = llm + rb;
    if (total > 0) {
        const pct = ((llm / total) * 100).toFixed(0);
        document.getElementById('kpiMethodRatio').textContent = pct + '%';
        document.getElementById('kpiMethodDetail').textContent =
            `${llm} LLM · ${rb} Rule-Based`;
    } else {
        document.getElementById('kpiMethodRatio').textContent = '—';
    }
}

// ── Charts ───────────────────────────────────────────────────────────────────
const chartColors = {
    purple: 'rgba(99, 102, 241, 0.8)',
    purpleLight: 'rgba(99, 102, 241, 0.15)',
    cyan: 'rgba(6, 182, 212, 0.8)',
    cyanLight: 'rgba(6, 182, 212, 0.15)',
    amber: 'rgba(245, 158, 11, 0.8)',
    amberLight: 'rgba(245, 158, 11, 0.15)',
    green: 'rgba(16, 185, 129, 0.8)',
    greenLight: 'rgba(16, 185, 129, 0.15)',
    red: 'rgba(239, 68, 68, 0.8)',
    violet: 'rgba(139, 92, 246, 0.8)',
    violetLight: 'rgba(139, 92, 246, 0.15)',
    slate: 'rgba(100, 116, 139, 0.8)',
    slateLight: 'rgba(100, 116, 139, 0.15)',
};

// Global chart defaults
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(17, 24, 39, 0.95)';
Chart.defaults.plugins.tooltip.titleColor = '#f1f5f9';
Chart.defaults.plugins.tooltip.bodyColor = '#94a3b8';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.08)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.padding = 12;

function renderCharts(stats) {
    renderScoreDistChart(stats.score_distribution);
    renderDomainChart(stats.domain_breakdown);
    renderTrendChart(stats.recent_trend);
    renderMethodChart(stats.method_breakdown);
}

function destroyChart(key) {
    if (state.charts[key]) {
        state.charts[key].destroy();
        state.charts[key] = null;
    }
}

function renderScoreDistChart(distribution) {
    destroyChart('scoreDist');
    const ctx = document.getElementById('chartScoreDist').getContext('2d');

    const labels = ['0-1', '1-2', '2-3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9-10'];
    const bgColors = distribution.map((_, i) => {
        if (i < 3) return 'rgba(239, 68, 68, 0.7)';
        if (i < 5) return 'rgba(249, 115, 22, 0.7)';
        if (i < 7) return 'rgba(251, 191, 36, 0.7)';
        return 'rgba(16, 185, 129, 0.7)';
    });
    const borderColors = distribution.map((_, i) => {
        if (i < 3) return 'rgba(239, 68, 68, 1)';
        if (i < 5) return 'rgba(249, 115, 22, 1)';
        if (i < 7) return 'rgba(251, 191, 36, 1)';
        return 'rgba(16, 185, 129, 1)';
    });

    state.charts.scoreDist = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Evaluations',
                data: distribution,
                backgroundColor: bgColors,
                borderColor: borderColors,
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b' },
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        color: '#64748b',
                        stepSize: 1,
                        callback: v => Number.isInteger(v) ? v : '',
                    },
                },
            },
        },
    });
}

function renderDomainChart(breakdown) {
    destroyChart('domain');
    const ctx = document.getElementById('chartDomain').getContext('2d');

    const labels = Object.keys(breakdown).map(d => d.toUpperCase());
    const data = Object.values(breakdown);
    const colorMap = {
        dsa: [chartColors.purple, chartColors.purpleLight],
        dbms: [chartColors.cyan, chartColors.cyanLight],
        os: [chartColors.amber, chartColors.amberLight],
    };
    const bg = Object.keys(breakdown).map(d => (colorMap[d] || [chartColors.slate])[0]);
    const hover = Object.keys(breakdown).map(d => (colorMap[d] || [chartColors.slate, chartColors.slateLight])[1]);

    state.charts.domain = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: bg,
                hoverBackgroundColor: hover,
                borderWidth: 0,
                spacing: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { position: 'bottom' },
            },
        },
    });
}

function renderTrendChart(trend) {
    destroyChart('trend');
    const ctx = document.getElementById('chartTrend').getContext('2d');

    const labels = trend.map(t => {
        const d = new Date(t.date);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const scores = trend.map(t => t.avg_score);
    const counts = trend.map(t => t.count);

    state.charts.trend = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Avg Score',
                    data: scores,
                    borderColor: chartColors.purple,
                    backgroundColor: chartColors.purpleLight,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: chartColors.purple,
                    borderWidth: 2,
                },
                {
                    label: 'Evaluations',
                    data: counts,
                    borderColor: chartColors.cyan,
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.4,
                    pointRadius: 3,
                    borderWidth: 1.5,
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { position: 'bottom' },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', maxTicksLimit: 10 },
                },
                y: {
                    beginAtZero: true,
                    max: 10,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b' },
                    title: { display: true, text: 'Score', color: '#64748b' },
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    grid: { display: false },
                    ticks: {
                        color: '#64748b',
                        stepSize: 1,
                        callback: v => Number.isInteger(v) ? v : '',
                    },
                    title: { display: true, text: 'Count', color: '#64748b' },
                },
            },
        },
    });
}

function renderMethodChart(breakdown) {
    destroyChart('method');
    const ctx = document.getElementById('chartMethod').getContext('2d');

    const llm = breakdown.llm || 0;
    const rb = breakdown.rule_based || 0;

    state.charts.method = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['LLM', 'Rule-Based'],
            datasets: [{
                data: [llm, rb],
                backgroundColor: [chartColors.violet, chartColors.slate],
                hoverBackgroundColor: [chartColors.violetLight, chartColors.slateLight],
                borderWidth: 0,
                spacing: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { position: 'bottom' },
            },
        },
    });
}

// ── Logs Table ───────────────────────────────────────────────────────────────
async function loadLogs() {
    try {
        const params = new URLSearchParams();
        params.set('page', state.currentPage);
        params.set('page_size', state.pageSize);
        params.set('sort_by', state.sortBy);
        params.set('sort_order', state.sortOrder);

        const f = state.filters;
        if (f.search) params.set('search', f.search);
        if (f.domain) params.set('domain', f.domain);
        if (f.method) params.set('evaluation_method', f.method);
        if (f.minScore !== undefined && f.minScore !== '') params.set('min_score', f.minScore);
        if (f.maxScore !== undefined && f.maxScore !== '') params.set('max_score', f.maxScore);

        const data = await fetchJSON('/api/logs?' + params.toString());
        renderTable(data.logs);
        renderPagination(data);
    } catch (e) {
        console.error('Failed to load logs:', e);
        document.getElementById('logsBody').innerHTML = `
            <tr><td colspan="7">
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <h3>Error Loading Logs</h3>
                    <p>${escapeHtml(e.message)}</p>
                </div>
            </td></tr>`;
    }
}

function renderTable(logs) {
    const tbody = document.getElementById('logsBody');

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7">
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <h3>No Evaluation Logs Found</h3>
                    <p>Submit evaluations via the API or use the "New Evaluation" button above.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr onclick="openDetail(${log.id})" title="Click to view details">
            <td style="color:var(--text-muted); font-size:0.8rem;">#${log.id}</td>
            <td style="white-space:nowrap; font-size:0.8rem;">${formatTimestamp(log.timestamp)}</td>
            <td><span class="badge badge-${log.domain}">${log.domain.toUpperCase()}</span></td>
            <td class="truncated">${escapeHtml(log.question)}</td>
            <td><span class="score-badge ${scoreClass(log.score)}">${log.score.toFixed(1)}</span></td>
            <td>
                <div class="confidence-bar-wrapper">
                    <div class="confidence-bar">
                        <div class="confidence-bar-fill" style="width:${(log.confidence * 100).toFixed(0)}%"></div>
                    </div>
                    <span class="confidence-value">${(log.confidence * 100).toFixed(0)}%</span>
                </div>
            </td>
            <td><span class="badge badge-${log.evaluation_method}">${log.evaluation_method === 'llm' ? 'LLM' : 'Rule-Based'}</span></td>
        </tr>
    `).join('');
}

function renderPagination(data) {
    const container = document.getElementById('pagination');
    const { page, total_pages, total } = data;

    if (total_pages <= 1) {
        container.innerHTML = `<span class="pagination-info">Showing all ${total} records</span>`;
        return;
    }

    const start = (page - 1) * state.pageSize + 1;
    const end = Math.min(page * state.pageSize, total);

    let pages = [];
    const maxVisible = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    let endPage = Math.min(total_pages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
    }

    container.innerHTML = `
        <span class="pagination-info">Showing ${start}–${end} of ${total} records</span>
        <div class="pagination-controls">
            <button class="page-btn" onclick="goToPage(1)" ${page === 1 ? 'disabled' : ''}>«</button>
            <button class="page-btn" onclick="goToPage(${page - 1})" ${page === 1 ? 'disabled' : ''}>‹</button>
            ${pages.map(p => `
                <button class="page-btn ${p === page ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>
            `).join('')}
            <button class="page-btn" onclick="goToPage(${page + 1})" ${page === total_pages ? 'disabled' : ''}>›</button>
            <button class="page-btn" onclick="goToPage(${total_pages})" ${page === total_pages ? 'disabled' : ''}>»</button>
        </div>
    `;
}

function goToPage(page) {
    state.currentPage = page;
    loadLogs();
}

// ── Sorting ──────────────────────────────────────────────────────────────────
function sortTable(column) {
    if (state.sortBy === column) {
        state.sortOrder = state.sortOrder === 'desc' ? 'asc' : 'desc';
    } else {
        state.sortBy = column;
        state.sortOrder = 'desc';
    }
    state.currentPage = 1;

    // Update sort indicators
    document.querySelectorAll('.data-table thead th').forEach(th => {
        th.classList.remove('sorted');
        const icon = th.querySelector('.sort-icon');
        if (icon) icon.textContent = '↕';
    });
    const activeTh = document.querySelector(`th[data-sort="${column}"]`);
    if (activeTh) {
        activeTh.classList.add('sorted');
        const icon = activeTh.querySelector('.sort-icon');
        if (icon) icon.textContent = state.sortOrder === 'desc' ? '↓' : '↑';
    }

    loadLogs();
}

// ── Filters ──────────────────────────────────────────────────────────────────
let debounceTimer = null;
function debouncedFilter() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(applyFilters, 350);
}

function applyFilters() {
    state.filters = {
        search: document.getElementById('filterSearch').value.trim() || undefined,
        domain: document.getElementById('filterDomain').value || undefined,
        method: document.getElementById('filterMethod').value || undefined,
        minScore: document.getElementById('filterMinScore').value || undefined,
        maxScore: document.getElementById('filterMaxScore').value || undefined,
    };
    state.currentPage = 1;
    loadLogs();
}

function clearFilters() {
    document.getElementById('filterSearch').value = '';
    document.getElementById('filterDomain').value = '';
    document.getElementById('filterMethod').value = '';
    document.getElementById('filterMinScore').value = '';
    document.getElementById('filterMaxScore').value = '';
    state.filters = {};
    state.currentPage = 1;
    loadLogs();
}

// ── Detail Modal ─────────────────────────────────────────────────────────────
async function openDetail(logId) {
    try {
        const log = await fetchJSON(`/api/logs/${logId}`);
        const modal = document.getElementById('detailModal');

        document.getElementById('modalMeta').innerHTML = `
            <div class="modal-meta-item">
                <span class="meta-label">ID</span>
                <span class="meta-value">#${log.id}</span>
            </div>
            <div class="modal-meta-item">
                <span class="meta-label">Timestamp</span>
                <span class="meta-value">${formatTimestamp(log.timestamp)}</span>
            </div>
            <div class="modal-meta-item">
                <span class="meta-label">Domain</span>
                <span class="meta-value"><span class="badge badge-${log.domain}">${log.domain.toUpperCase()}</span></span>
            </div>
            <div class="modal-meta-item">
                <span class="meta-label">Score</span>
                <span class="meta-value"><span class="score-badge ${scoreClass(log.score)}">${log.score.toFixed(1)} / 10</span></span>
            </div>
            <div class="modal-meta-item">
                <span class="meta-label">Confidence</span>
                <span class="meta-value">${(log.confidence * 100).toFixed(0)}%</span>
            </div>
            <div class="modal-meta-item">
                <span class="meta-label">Method</span>
                <span class="meta-value"><span class="badge badge-${log.evaluation_method}">${log.evaluation_method === 'llm' ? 'LLM' : 'Rule-Based'}</span></span>
            </div>
            ${log.llm_provider ? `
            <div class="modal-meta-item">
                <span class="meta-label">Provider</span>
                <span class="meta-value">${log.llm_provider}</span>
            </div>` : ''}
        `;

        document.getElementById('modalBody').innerHTML = `
            <div class="modal-section">
                <h3>Question</h3>
                <div class="content-block">${escapeHtml(log.question)}</div>
            </div>
            <div class="modal-section">
                <h3>Candidate's Answer</h3>
                <div class="content-block">${escapeHtml(log.answer)}</div>
            </div>
            <div class="modal-section">
                <h3>Feedback</h3>
                <div class="content-block feedback-block">${escapeHtml(log.feedback)}</div>
            </div>
        `;

        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    } catch (e) {
        showToast('Failed to load details: ' + e.message, 'error');
    }
}

function closeModal() {
    document.getElementById('detailModal').classList.remove('active');
    document.body.style.overflow = '';
}

// Close modal on outside click or Escape
document.addEventListener('click', e => {
    if (e.target.classList.contains('modal-overlay')) closeModal();
});
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
});

// ── Evaluate Form ────────────────────────────────────────────────────────────
function openEvalForm() {
    document.getElementById('evalFormSection').style.display = 'block';
    document.getElementById('evalFormSection').scrollIntoView({ behavior: 'smooth' });
}

function closeEvalForm() {
    document.getElementById('evalFormSection').style.display = 'none';
}

async function submitEvaluation(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitEval');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Evaluating...';

    try {
        const body = {
            question: document.getElementById('evalQuestion').value.trim(),
            answer: document.getElementById('evalAnswer').value.trim(),
        };
        const domain = document.getElementById('evalDomain').value;
        if (domain) body.domain = domain;

        const result = await postJSON('/evaluate', body);
        showToast(`Score: ${result.score.toFixed(1)} / 10 — ${result.feedback.substring(0, 80)}...`, 'success');

        // Reset form
        document.getElementById('evalForm').reset();
        closeEvalForm();

        // Refresh dashboard data
        await refreshAll();
    } catch (err) {
        showToast('Evaluation failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>⚡</span> Evaluate';
    }
}

// ── Utilities ────────────────────────────────────────────────────────────────
function scoreClass(score) {
    if (score >= 8) return 'score-excellent';
    if (score >= 6) return 'score-good';
    if (score >= 4) return 'score-average';
    if (score >= 2) return 'score-poor';
    return 'score-bad';
}

function formatTimestamp(ts) {
    try {
        const d = new Date(ts);
        return d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
        }) + ' ' + d.toLocaleTimeString('en-US', {
            hour: '2-digit', minute: '2-digit', hour12: true,
        });
    } catch {
        return ts;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.className = 'toast ' + type;
    toast.innerHTML = `${type === 'success' ? '✅' : '❌'} ${escapeHtml(message)}`;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 4500);
}
