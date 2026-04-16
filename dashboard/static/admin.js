/**
 * KALGA Admin Dashboard - JavaScript
 */

const API_URL = (location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.protocol === 'file:')
    ? 'http://localhost:8001'
    : location.origin;

// State
const state = {
    token: localStorage.getItem('kalga_admin_token'),
    user: JSON.parse(localStorage.getItem('kalga_admin_user') || 'null'),
    currentSection: 'overview',
    merchantsPage: 1
};

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Check if already logged in
    if (state.token && state.user) {
        showDashboard();
        refreshDashboard();
    } else {
        showLogin();
    }

    // Setup navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            navigateTo(section);
        });
    });

    // Setup login form
    document.getElementById('login-form').addEventListener('submit', handleLogin);
});

// ============================================
// AUTHENTICATION
// ============================================

async function handleLogin(e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('login-error');

    // Clear previous error
    errorEl.textContent = '';
    errorEl.style.color = '#f56565';

    // Show loading
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = 'Connexion...';
    submitBtn.disabled = true;

    try {
        console.log('Tentative de connexion a:', `${API_URL}/api/auth/login`);

        const response = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        console.log('Response status:', response.status);

        const data = await response.json();
        console.log('Response data:', data);

        if (!response.ok) {
            throw new Error(data.detail || 'Erreur de connexion');
        }

        // Check if admin
        if (data.user.role !== 'admin') {
            throw new Error('Acces reserve aux administrateurs');
        }

        // Save auth data
        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('kalga_admin_token', data.access_token);
        localStorage.setItem('kalga_admin_user', JSON.stringify(data.user));

        showDashboard();
        refreshDashboard();

    } catch (error) {
        console.error('Login error:', error);

        // Check if it's a network error
        if (error.message === 'Failed to fetch') {
            errorEl.textContent = "Impossible de contacter l'API. Verifiez que le serveur est demarre (port 8001).";
        } else {
            errorEl.textContent = error.message;
        }
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('kalga_admin_token');
    localStorage.removeItem('kalga_admin_user');
    showLogin();
}

function showLogin() {
    document.getElementById('login-screen').style.display = 'grid';
    document.getElementById('dashboard').style.display = 'none';
}

function showDashboard() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'flex';
    document.getElementById('admin-email').textContent = state.user?.email || 'Admin';
}

// ============================================
// API HELPERS
// ============================================

async function apiGet(endpoint) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${state.token}`,
            'Content-Type': 'application/json'
        }
    });

    if (response.status === 401) {
        logout();
        throw new Error('Session expiree');
    }

    return response.json();
}

async function apiPost(endpoint, data) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${state.token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    if (response.status === 401) {
        logout();
        throw new Error('Session expiree');
    }

    return response.json();
}

async function apiPut(endpoint, data) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${state.token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    if (response.status === 401) {
        logout();
        throw new Error('Session expiree');
    }

    return response.json();
}

// ============================================
// NAVIGATION
// ============================================

function navigateTo(section) {
    state.currentSection = section;

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });

    // Show section
    document.querySelectorAll('.section').forEach(s => {
        s.classList.toggle('active', s.id === `section-${section}`);
    });

    // Load section data
    switch (section) {
        case 'overview':
            loadDashboardStats();
            break;
        case 'activations':
            loadPendingActivations();
            loadActivationHistory();
            break;
        case 'merchants':
            loadMerchants();
            break;
        case 'whatsapp':
            loadWhatsAppStatus();
            break;
        case 'subscriptions':
            loadAdmins();
            break;
        case 'audit':
            loadAuditLogs();
            break;
    }
}

// ============================================
// DASHBOARD OVERVIEW
// ============================================

async function refreshDashboard() {
    await loadDashboardStats();
    // Also load pending activations count for badge
    loadPendingActivationsCount();
}

async function loadPendingActivationsCount() {
    try {
        const data = await apiGet('/api/admin/pending-activations');
        const badge = document.getElementById('pending-activations-badge');

        if (data.count > 0) {
            badge.textContent = data.count;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }
    } catch (error) {
        console.error('Erreur chargement compteur activations:', error);
    }
}

function showStatSkeletons() {
    document.querySelectorAll('.stat-card-value').forEach(el => {
        el.innerHTML = '<div class="skeleton" style="height:28px;width:60px;border-radius:6px;display:inline-block;"></div>';
    });
    document.querySelectorAll('.stat-card-sub').forEach(el => {
        el.innerHTML = '<div class="skeleton" style="height:10px;width:80px;border-radius:6px;display:inline-block;"></div>';
    });
    const bars = document.getElementById('subscription-bars');
    if (bars) bars.innerHTML = Array.from({length:4}).map(() => `
        <div style="display:flex;flex-direction:column;gap:0.4rem;margin-bottom:0.75rem;">
            <div style="display:flex;justify-content:space-between;"><div class="skeleton" style="height:10px;width:60px;border-radius:4px;"></div><div class="skeleton" style="height:10px;width:20px;border-radius:4px;"></div></div>
            <div class="skeleton" style="height:6px;border-radius:100px;"></div>
        </div>`).join('');
    const exp = document.getElementById('expiring-list');
    if (exp) exp.innerHTML = Array.from({length:3}).map(() => `
        <tr><td><div class="skeleton" style="height:11px;width:120px;border-radius:4px;margin-bottom:0.3rem;"></div><div class="skeleton" style="height:9px;width:80px;border-radius:4px;"></div></td>
        <td><div class="skeleton" style="height:20px;width:50px;border-radius:100px;"></div></td>
        <td><div class="skeleton" style="height:10px;width:70px;border-radius:4px;"></div></td>
        <td><div class="skeleton" style="height:24px;width:64px;border-radius:6px;"></div></td></tr>`).join('');
}

async function loadDashboardStats() {
    showStatSkeletons();
    try {
        const data = await apiGet('/api/admin/dashboard');

        // Update primary KPI cards
        document.getElementById('stat-merchants-total').textContent = data.merchants.total;
        document.getElementById('stat-merchants-active').textContent = `${data.merchants.active} actifs`;
        document.getElementById('stat-conversations-total').textContent = data.conversations.total;
        document.getElementById('stat-conversations-today').textContent = `${data.conversations.today} aujourd'hui`;
        document.getElementById('stat-sales-total').textContent = data.sales.total;
        document.getElementById('stat-messages-total').textContent = formatNumber(data.messages.total);

        // Secondary KPI row
        const newEl = document.getElementById('stat-merchants-month');
        if (newEl) newEl.innerHTML = `<i class="fas fa-arrow-trend-up"></i> +${data.merchants.this_month || 0} ce mois`;
        const kpiNew = document.getElementById('kpi-new-merchants');
        if (kpiNew) kpiNew.textContent = data.merchants.this_month || 0;
        const kpiExp = document.getElementById('kpi-expiring');
        if (kpiExp) kpiExp.textContent = data.subscriptions.expiring_soon || 0;

        // Overview date
        const dateEl = document.getElementById('overview-date');
        if (dateEl) {
            const now = new Date();
            dateEl.textContent = now.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
        }

        // Subscription bars
        renderSubscriptionBars(data.subscriptions.by_plan);

        // Expiring soon
        renderExpiringSoon(data.expiring_subscriptions);

        // Load WhatsApp KPIs
        loadWhatsAppKPIs();

    } catch (error) {
        console.error('Erreur chargement dashboard:', error);
    }
}

async function loadWhatsAppKPIs() {
    try {
        const data = await apiGet('/api/admin/system/whatsapp-status');
        const conn = document.getElementById('kpi-wa-connected');
        const disc = document.getElementById('kpi-wa-disconnected');
        if (conn) conn.textContent = data.connected;
        if (disc) disc.textContent = data.disconnected;
    } catch (e) {}
}

function renderSubscriptionBars(plans) {
    const container = document.getElementById('subscription-bars');
    const total = Object.values(plans).reduce((a, b) => a + b, 0) || 1;

    const planNames = { trial: 'Trial', starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise' };

    container.innerHTML = Object.entries(planNames).map(([key, label]) => {
        const count = plans[key] || 0;
        const percent = Math.round((count / total) * 100);

        return `
            <div class="sub-bar-item">
                <div class="sub-bar-header">
                    <span class="sub-bar-label">${label}</span>
                    <span class="sub-bar-count">${count}</span>
                </div>
                <div class="sub-bar-track">
                    <div class="sub-bar-fill ${key}" style="width: ${percent}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

function renderExpiringSoon(subscriptions) {
    const tbody = document.getElementById('expiring-list');

    if (!subscriptions.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:2rem;color:var(--text-muted);font-size:0.82rem;"><i class="fas fa-circle-check" style="display:block;font-size:1.2rem;margin-bottom:0.4rem;opacity:0.3;"></i>Aucun abonnement expirant bientôt</td></tr>';
        return;
    }

    tbody.innerHTML = subscriptions.map(s => {
        const expiresAt = s.trial_ends_at || s.end_date;
        const expiresDate = expiresAt ? new Date(expiresAt).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' }) : '—';
        const planLabels = { trial: 'Trial', starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise' };

        return `
            <tr>
                <td>
                    <div class="exp-merchant-name">${s.name || '—'}</div>
                    <div class="exp-merchant-phone">${s.phone || ''}</div>
                </td>
                <td><span class="status-badge ${s.plan || 'trial'}">${planLabels[s.plan] || s.plan || 'trial'}</span></td>
                <td><span class="exp-date-chip"><i class="fas fa-hourglass-half"></i>${expiresDate}</span></td>
                <td>
                    <button onclick="openSubscriptionModal(${s.merchant_id})" class="btn-mc-detail">
                        <i class="fas fa-pen"></i> Modifier
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ============================================
// MERCHANTS
// ============================================

function setMerchantFilter(btn, value) {
    document.getElementById('merchant-filter').value = value;
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    state.merchantsPage = 1;
    loadMerchants();
}

async function loadMerchants() {
    const container = document.getElementById('merchants-list');
    showMerchantSkeletons(container);

    try {
        const filter = document.getElementById('merchant-filter').value;
        const filterParam = filter ? `&status_filter=${filter}` : '';
        const data = await apiGet(`/api/admin/merchants?page=${state.merchantsPage}&limit=20${filterParam}`);

        renderMerchantsList(container, data.merchants, data.total);
        renderPagination(data.page, data.pages, 'merchants');

    } catch (error) {
        console.error('Erreur chargement marchands:', error);
        container.innerHTML = `<div class="merchants-empty"><i class="fas fa-triangle-exclamation"></i><h3>Erreur de chargement</h3><p>Impossible de récupérer les marchands</p></div>`;
    }
}

function showMerchantSkeletons(container, count = 6) {
    container.innerHTML = Array.from({ length: count }).map(() => `
        <div class="merchant-card-skeleton">
            <div class="sk-header">
                <div class="skeleton sk-avatar"></div>
                <div class="sk-title">
                    <div class="skeleton sk-line-lg"></div>
                    <div class="skeleton sk-line-sm"></div>
                </div>
            </div>
            <div class="sk-pills">
                <div class="skeleton sk-badge"></div>
                <div class="skeleton sk-badge"></div>
            </div>
            <div>
                <div class="skeleton sk-line-md" style="margin-bottom:0.4rem"></div>
                <div class="skeleton sk-line-xs"></div>
            </div>
            <div class="sk-footer">
                <div class="skeleton sk-line-sm"></div>
                <div class="skeleton sk-badge" style="width:80px;height:28px;border-radius:8px;"></div>
            </div>
        </div>
    `).join('');
}

function renderMerchantsList(container, merchants, total) {
    if (!merchants.length) {
        container.innerHTML = `
            <div class="merchants-empty">
                <i class="fas fa-store-slash"></i>
                <h3>Aucun marchand trouvé</h3>
                <p>Essayez un autre filtre ou actualisez la page</p>
            </div>`;
        return;
    }

    const planColors = { trial: '#60a5fa', starter: '#a78bfa', pro: '#34d399', enterprise: '#f59e0b' };
    const planLabels = { trial: 'Trial', starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise' };
    const subStatusLabels = { active: 'Actif', trial: 'En essai', expired: 'Expiré', cancelled: 'Annulé', suspended: 'Suspendu' };

    const countChip = `<div class="merchants-count-chip"><strong>${total}</strong> marchand${total > 1 ? 's' : ''}</div>`;

    const cards = merchants.map(m => {
        const waKey = m.whatsapp_status === 'ready' ? 'connected' : 'disconnected';
        const waLabel = waKey === 'connected' ? 'WhatsApp connecté' : (m.whatsapp_status === 'not_registered' ? 'Non enregistré' : 'Hors ligne');
        const waIcon = waKey === 'connected' ? 'fa-circle-check' : 'fa-circle-xmark';

        const userStatus = m.is_active === null || m.is_active === undefined ? 'trial' : (m.is_active ? 'active' : 'inactive');
        const userLabel = m.is_active === null || m.is_active === undefined ? 'Sans compte' : (m.is_active ? 'Actif' : 'Inactif');

        const initial = (m.name || '?').replace(/[^a-zA-Z0-9]/g, '').charAt(0).toUpperCase() || '?';
        const plan = m.plan || 'trial';
        const planLabel = planLabels[plan] || plan;
        const planColor = planColors[plan] || '#718096';

        const used = m.real_messages_count || 0;
        const limit = m.messages_limit || 500;
        const usagePct = Math.min(100, Math.round((used / limit) * 100));
        const usageClass = usagePct >= 90 ? 'usage--warn' : 'usage--ok';

        const createdDate = m.merchant_created_at || m.user_created_at;
        const dateLabel = createdDate ? new Date(createdDate).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';

        return `
            <div class="merchant-card mc--${waKey}">
                <div class="mc-header">
                    <div class="mc-identity">
                        <div class="mc-avatar av--${waKey}">${initial}</div>
                        <div class="mc-name-block">
                            <span class="mc-name">${m.name || 'Marchand inconnu'}</span>
                            <span class="mc-biz">${m.business_name || m.phone || '—'}</span>
                        </div>
                    </div>
                    <div class="mc-badges">
                        <span class="mc-wa-badge wab--${waKey}">
                            <span class="mc-wa-badge-dot"></span>
                            ${waKey === 'connected' ? 'Connecté' : (m.whatsapp_status === 'not_registered' ? 'Non enregistré' : 'Hors ligne')}
                        </span>
                        <span class="status-badge ${userStatus}">${userLabel}</span>
                    </div>
                </div>

                <div class="mc-meta">
                    <div class="mc-meta-row">
                        <i class="fas fa-phone"></i>
                        <span>${m.phone || '—'}</span>
                    </div>
                    <div class="mc-meta-row">
                        <i class="fas fa-tag"></i>
                        <span style="color:${planColor};font-weight:600;">${planLabel}</span>
                        ${m.subscription_status ? `<span style="margin-left:auto;font-size:0.69rem;color:var(--text-muted);">${subStatusLabels[m.subscription_status] || m.subscription_status}</span>` : ''}
                    </div>
                </div>

                <div class="mc-usage">
                    <div class="mc-usage-label">
                        <span>Messages</span>
                        <strong>${used.toLocaleString()} / ${limit.toLocaleString()}</strong>
                    </div>
                    <div class="mc-usage-track">
                        <div class="mc-usage-fill ${usageClass}" style="width:${Math.max(usagePct, 2)}%"></div>
                    </div>
                </div>

                <div class="mc-footer">
                    <span class="mc-footer-info">
                        <i class="fas fa-calendar-plus"></i>
                        Ajouté le ${dateLabel}
                    </span>
                    <button onclick="showMerchantDetail(${m.merchant_id})" class="btn-mc-detail">
                        <i class="fas fa-arrow-right"></i> Détails
                    </button>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = countChip + `<div class="merchants-grid">${cards}</div>`;
}

function renderPagination(currentPage, totalPages, type) {
    const container = document.getElementById(`${type}-pagination`);

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';

    html += `<button ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${type}, ${currentPage - 1})">Precedent</button>`;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage('${type}', ${i})">${i}</button>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += `<span style="padding: 0.5rem">...</span>`;
        }
    }

    html += `<button ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage('${type}', ${currentPage + 1})">Suivant</button>`;

    container.innerHTML = html;
}

function goToPage(type, page) {
    if (type === 'merchants') {
        state.merchantsPage = page;
        loadMerchants();
    }
}

async function showMerchantDetail(merchantId) {
    try {
        const data = await apiGet(`/api/admin/merchants/${merchantId}`);

        document.getElementById('modal-merchant-name').textContent = data.merchant.name;

        const content = document.getElementById('merchant-detail-content');
        content.innerHTML = `
            <div class="merchant-detail-grid">
                <div class="detail-section">
                    <h4>Informations</h4>
                    <div class="detail-row">
                        <span class="detail-label">Nom</span>
                        <span class="detail-value">${data.merchant.name}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Commerce</span>
                        <span class="detail-value">${data.merchant.business_name || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Telephone</span>
                        <span class="detail-value">${data.merchant.phone}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Adresse</span>
                        <span class="detail-value">${data.merchant.address || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">WhatsApp</span>
                        <span class="status-badge ${data.whatsapp_status === 'ready' ? 'connected' : 'disconnected'}">
                            ${data.whatsapp_status === 'ready' ? 'Connecté' : (data.whatsapp_status === 'not_registered' ? 'Non enregistré' : 'Hors ligne')}
                        </span>
                    </div>
                </div>

                <div class="detail-section">
                    <h4>Abonnement</h4>
                    ${data.subscription ? `
                        <div class="detail-row">
                            <span class="detail-label">Plan</span>
                            <span class="status-badge ${data.subscription.plan}">${{ trial: 'Trial', starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise' }[data.subscription.plan] || data.subscription.plan}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Statut</span>
                            <span class="status-badge ${data.subscription.status}">${{ active: 'Actif', trial: 'En essai', expired: 'Expiré', cancelled: 'Annulé', suspended: 'Suspendu' }[data.subscription.status] || data.subscription.status}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Messages</span>
                            <span class="detail-value">${data.real_messages_count ?? data.subscription.messages_used} / ${data.subscription.messages_limit}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Expire le</span>
                            <span class="detail-value">${formatDate(data.subscription.trial_ends_at || data.subscription.end_date)}</span>
                        </div>
                    ` : '<p style="color: var(--text-muted)">Aucun abonnement</p>'}
                </div>

                <div class="detail-section">
                    <h4>Statistiques</h4>
                    <div class="detail-row">
                        <span class="detail-label">Produits</span>
                        <span class="detail-value">${data.stats.products}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Conversations</span>
                        <span class="detail-value">${data.stats.conversations}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Ventes</span>
                        <span class="detail-value">${data.stats.sales}</span>
                    </div>
                </div>

                <div class="detail-section">
                    <h4>Compte utilisateur</h4>
                    ${data.user ? `
                        <div class="detail-row">
                            <span class="detail-label">Email</span>
                            <span class="detail-value">${data.user.email}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Status</span>
                            <span class="status-badge ${data.user.is_active ? 'active' : 'inactive'}">
                                ${data.user.is_active ? 'Actif' : 'Inactif'}
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Derniere connexion</span>
                            <span class="detail-value">${formatDate(data.user.last_login) || 'Jamais'}</span>
                        </div>
                    ` : '<p style="color: var(--text-muted)">Aucun compte utilisateur</p>'}
                </div>
            </div>

            <div style="margin-top: 1.5rem; display: flex; gap: 1rem;">
                ${data.user ? `
                    <button onclick="toggleMerchantStatus(${merchantId}, ${!data.user.is_active})"
                            class="btn ${data.user.is_active ? 'btn-warning' : 'btn-primary'}">
                        ${data.user.is_active ? 'Desactiver' : 'Activer'} le compte
                    </button>
                ` : ''}
                <button onclick="openSubscriptionModal(${merchantId})" class="btn btn-secondary">
                    Modifier l'abonnement
                </button>
            </div>
        `;

        openModal('merchant-modal');

    } catch (error) {
        console.error('Erreur chargement detail marchand:', error);
        alert('Erreur lors du chargement des details');
    }
}

async function toggleMerchantStatus(merchantId, newStatus) {
    try {
        await apiPut(`/api/admin/merchants/${merchantId}/status`, {
            is_active: newStatus,
            reason: newStatus ? 'Activation manuelle' : 'Desactivation manuelle'
        });

        closeModal('merchant-modal');
        loadMerchants();
        alert(`Marchand ${newStatus ? 'active' : 'desactive'} avec succes`);

    } catch (error) {
        console.error('Erreur mise a jour status:', error);
        alert('Erreur lors de la mise a jour');
    }
}

function openSubscriptionModal(merchantId) {
    document.getElementById('sub-merchant-id').value = merchantId;
    closeModal('merchant-modal');
    openModal('subscription-modal');
}

async function saveSubscription() {
    const merchantId = document.getElementById('sub-merchant-id').value;
    const plan = document.getElementById('sub-plan').value;
    const duration = parseInt(document.getElementById('sub-duration').value);
    const messages = parseInt(document.getElementById('sub-messages').value);
    const products = parseInt(document.getElementById('sub-products').value);

    try {
        await apiPut(`/api/admin/merchants/${merchantId}/subscription`, {
            plan,
            duration_months: duration,
            messages_limit: messages,
            products_limit: products
        });

        closeModal('subscription-modal');
        loadMerchants();
        loadDashboardStats();
        alert('Abonnement mis a jour avec succes');

    } catch (error) {
        console.error('Erreur mise a jour abonnement:', error);
        alert('Erreur lors de la mise a jour');
    }
}

// ============================================
// WHATSAPP STATUS
// ============================================

async function loadWhatsAppStatus() {
    const grid = document.getElementById('whatsapp-grid');
    grid.innerHTML = Array.from({length: 5}).map(() => `
        <div class="wa-card" style="gap:0.9rem;">
            <div class="wa-card-left">
                <div class="skeleton" style="width:40px;height:40px;border-radius:10px;flex-shrink:0;"></div>
                <div style="display:flex;flex-direction:column;gap:0.35rem;flex:1;">
                    <div class="skeleton" style="height:12px;width:40%;border-radius:4px;"></div>
                    <div class="skeleton" style="height:10px;width:60%;border-radius:4px;"></div>
                </div>
            </div>
            <div class="skeleton" style="height:22px;width:80px;border-radius:100px;"></div>
        </div>`).join('');

    try {
        const data = await apiGet('/api/admin/system/whatsapp-status');

        document.getElementById('wa-connected').textContent = data.connected;
        document.getElementById('wa-disconnected').textContent = data.disconnected;

        const grid = document.getElementById('whatsapp-grid');
        if (!data.statuses || data.statuses.length === 0) {
            grid.innerHTML = '<div class="wa-empty"><i class="fab fa-whatsapp"></i><p>Aucune session WhatsApp configurée</p></div>';
            return;
        }
        grid.innerHTML = data.statuses.map(s => {
            const statusClass = s.ready ? 'connected' : 'disconnected';
            const statusLabel = s.ready ? 'Connecté' : 'Déconnecté';
            const initial = s.name ? s.name.replace(/[^a-zA-Z0-9]/g, '').charAt(0).toUpperCase() || '#' : '#';
            return `
                <div class="wa-card ${statusClass}">
                    <div class="wa-card-left">
                        <div class="wa-card-avatar ${statusClass}">${initial}</div>
                        <div class="wa-card-info">
                            <span class="wa-card-name">${s.name}</span>
                            <span class="wa-card-phone"><i class="fas fa-phone-alt"></i>${s.phone}</span>
                        </div>
                    </div>
                    <div class="wa-card-right">
                        <span class="wa-badge ${statusClass}">
                            <span class="wa-badge-dot"></span>${statusLabel}
                        </span>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Erreur chargement status WhatsApp:', error);
    }
}

// ============================================
// AUDIT LOGS
// ============================================

async function loadAuditLogs() {
    const tbody = document.getElementById('audit-list');
    tbody.innerHTML = Array.from({length: 6}).map(() => `
        <tr>
            <td><div class="audit-skeleton-row" style="padding:0;border:none;">
                <div class="skeleton" style="height:10px;width:110px;border-radius:4px;"></div>
            </div></td>
            <td><div style="display:flex;align-items:center;gap:0.5rem;">
                <div class="skeleton" style="width:28px;height:28px;border-radius:50%;flex-shrink:0;"></div>
                <div class="skeleton" style="height:10px;width:120px;border-radius:4px;"></div>
            </div></td>
            <td><div class="skeleton" style="height:20px;width:90px;border-radius:100px;"></div></td>
            <td><div style="display:flex;gap:0.4rem;">
                <div class="skeleton" style="height:20px;width:70px;border-radius:6px;"></div>
                <div class="skeleton" style="height:20px;width:50px;border-radius:6px;"></div>
            </div></td>
        </tr>`).join('');

    try {
        const data = await apiGet('/api/admin/audit-logs?limit=50');

        if (!data.logs.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:3rem;color:var(--text-muted);font-size:0.85rem;"><i class="fas fa-shield-halved" style="opacity:0.2;font-size:1.5rem;display:block;margin-bottom:0.5rem;"></i>Aucun log d\'audit</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.map(log => {
            const initial = log.admin_email ? log.admin_email[0].toUpperCase() : '?';
            const actionLabel = formatAction(log.action);
            const actionClass = getActionClass(log.action);
            let detailsHtml = '';
            if (log.details) {
                try {
                    const d = typeof log.details === 'string' ? JSON.parse(log.details) : log.details;
                    detailsHtml = Object.entries(d).map(([k, v]) =>
                        `<span class="audit-detail-pill"><span class="audit-detail-key">${k}</span><span class="audit-detail-val">${v}</span></span>`
                    ).join('');
                } catch {
                    detailsHtml = `<span class="audit-detail-pill"><span class="audit-detail-val">${log.details}</span></span>`;
                }
            }
            return `
            <tr class="audit-row">
                <td><span class="audit-date"><i class="fas fa-clock"></i> ${formatDateTime(log.created_at)}</span></td>
                <td>
                    <span class="audit-admin">
                        <span class="audit-avatar">${initial}</span>
                        <span class="audit-email">${log.admin_email}</span>
                    </span>
                </td>
                <td><span class="audit-action-badge ${actionClass}">${actionLabel}</span></td>
                <td><span class="audit-details">${detailsHtml}</span></td>
            </tr>`;
        }).join('');

    } catch (error) {
        console.error('Erreur chargement logs:', error);
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:2rem;color:var(--text-muted);">Erreur de chargement</td></tr>';
    }
}

function formatAction(action) {
    const actions = {
        'merchant_status_update': 'Statut marchand',
        'subscription_update': 'Abonnement',
        'admin_created': 'Admin créé',
        'system_cleanup': 'Nettoyage',
        'activation_code_sent': 'Code envoyé',
        'login': 'Connexion',
        'logout': 'Déconnexion'
    };
    return actions[action] || action;
}

function getActionClass(action) {
    const classes = {
        'merchant_status_update': 'badge--blue',
        'subscription_update': 'badge--purple',
        'admin_created': 'badge--amber',
        'system_cleanup': 'badge--red',
        'activation_code_sent': 'badge--green',
        'login': 'badge--gray',
        'logout': 'badge--gray'
    };
    return classes[action] || 'badge--gray';
}

// ============================================
// SYSTEM ACTIONS
// ============================================

async function runCleanup() {
    if (!confirm('Voulez-vous vraiment nettoyer les abonnements expires et les conversations anciennes?')) {
        return;
    }

    try {
        const data = await apiPost('/api/admin/system/cleanup-expired', {});
        alert(`Nettoyage effectue:\n- ${data.expired_subscriptions_marked} abonnements marques comme expires\n- ${data.conversations_cleaned} conversations nettoyees`);
        loadDashboardStats();

    } catch (error) {
        console.error('Erreur nettoyage:', error);
        alert('Erreur lors du nettoyage');
    }
}

// ============================================
// ADMINS
// ============================================

async function loadAdmins() {
    try {
        const data = await apiGet('/api/admin/admins');
        const container = document.getElementById('admins-list');
        if (!container) return;

        if (!data.admins || !data.admins.length) {
            container.innerHTML = '<p style="color:var(--text-muted);font-size:0.8rem;">Aucun administrateur trouvé</p>';
            return;
        }

        container.innerHTML = data.admins.map(a => `
            <div class="admin-row">
                <div class="admin-row-avatar"><i class="fas fa-user-shield"></i></div>
                <div class="admin-row-info">
                    <span class="admin-row-name">${a.name || 'Admin'}</span>
                    <span class="admin-row-email">${a.email}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Erreur chargement admins:', error);
    }
}

function openCreateAdminModal() {
    document.getElementById('admin-new-name').value = '';
    document.getElementById('admin-new-email').value = '';
    document.getElementById('admin-new-password').value = '';
    openModal('create-admin-modal');
}

async function createAdmin() {
    const name = document.getElementById('admin-new-name').value.trim();
    const email = document.getElementById('admin-new-email').value.trim();
    const password = document.getElementById('admin-new-password').value;

    if (!name || !email || !password) {
        alert('Tous les champs sont requis');
        return;
    }

    try {
        await apiPost('/api/admin/admins', { name, email, password });
        closeModal('create-admin-modal');
        loadAdmins();
        alert('Administrateur créé avec succès');
    } catch (error) {
        console.error('Erreur création admin:', error);
        alert('Erreur lors de la création');
    }
}

// ============================================
// MODALS
// ============================================

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Close modal on outside click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// ============================================
// HELPERS
// ============================================

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('fr-FR');
}

function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

// ============================================
// ACTIVATIONS MANAGEMENT
// ============================================

async function loadPendingActivations() {
    const container = document.getElementById('pending-activations-list');
    container.innerHTML = Array.from({length: 3}).map(() => `
        <div class="merchant-card-skeleton">
            <div class="sk-header">
                <div class="skeleton sk-avatar"></div>
                <div class="sk-title">
                    <div class="skeleton sk-line-lg"></div>
                    <div class="skeleton sk-line-sm"></div>
                </div>
            </div>
            <div class="sk-pills">
                <div class="skeleton sk-badge"></div>
                <div class="skeleton sk-badge"></div>
            </div>
            <div class="skeleton sk-line-md"></div>
        </div>`).join('');

    try {
        const data = await apiGet('/api/admin/pending-activations');
        container.innerHTML = '';
        const emptyState = document.getElementById('pending-activations-empty');
        const badge = document.getElementById('pending-activations-badge');

        // Update badge
        if (data.count > 0) {
            badge.textContent = data.count;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }

        if (data.merchants.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';

        container.innerHTML = data.merchants.map((m, i) => {
            const name = m.business_name || m.name || 'Nouveau marchand';
            const initials = name.split(' ').filter(Boolean).map(w => w[0]).join('').toUpperCase().slice(0, 2) || 'M';
            const isConnected = m.whatsapp_connected;
            const hasCode = !!m.pending_code;
            return `
            <div class="activation-card ${isConnected ? 'ac--connected' : 'ac--disconnected'}" data-merchant-id="${m.id}" style="animation-delay:${i*0.07}s">
                <div class="ac-left">
                    <div class="ac-avatar ${isConnected ? 'ac-avatar--on' : 'ac-avatar--off'}">${initials}</div>
                    <div class="ac-wa-badge ${isConnected ? 'ac-wa-badge--on' : 'ac-wa-badge--off'}">
                        <i class="fab fa-whatsapp"></i>
                        <span>${isConnected ? 'Connecté' : 'Déconnecté'}</span>
                    </div>
                </div>
                <div class="ac-right">
                    <div class="ac-top-row">
                        <div class="ac-identity">
                            <h3 class="ac-name">${name}</h3>
                            <div class="ac-phone"><i class="fas fa-phone-alt"></i><span>${formatPhone(m.phone)}</span></div>
                        </div>
                        <div class="ac-registered">
                            <i class="fas fa-calendar-plus"></i>
                            <span>${formatDateTime(m.created_at)}</span>
                        </div>
                    </div>
                    ${hasCode ? `
                    <div class="ac-code-block">
                        <span class="ac-code-eyebrow"><i class="fas fa-key"></i>Code d'activation envoyé</span>
                        <div class="ac-code-row">
                            <span class="ac-code-value">${m.pending_code}</span>
                            ${m.pending_code_sent_at ? `<span class="ac-code-time"><i class="fas fa-clock"></i>${formatDateTime(m.pending_code_sent_at)}</span>` : ''}
                        </div>
                    </div>
                    ` : '<div class="ac-no-code"><i class="fas fa-hourglass-half"></i> En attente d\'envoi</div>'}
                    <button class="btn-send-code" onclick="sendActivationCode(${m.id}, this, ${isConnected ? 'true' : 'false'})">
                        <i class="fas fa-paper-plane"></i>
                        <span>${hasCode ? 'Renvoyer le code' : 'Envoyer le code'}</span>
                    </button>
                </div>
            </div>
        `}).join('');

    } catch (error) {
        console.error('Erreur chargement activations:', error);
    }
}

async function sendActivationCode(merchantId, btn, waConnected) {
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.classList.add('btn--loading');
    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i><span>Envoi en cours…</span>';

    try {
        const result = await apiPost(`/api/admin/send-activation/${merchantId}`);

        if (result.success) {
            btn.classList.remove('btn--loading');
            btn.classList.add('btn--success');
            btn.innerHTML = '<i class="fas fa-circle-check"></i><span>Code envoyé !</span>';
            btn.style.background = '';

            // Show the code
            alert(`Code envoye avec succes!\n\nCode: ${result.code}\n\n${result.message}`);

            // Reload the list after a delay
            setTimeout(() => {
                loadPendingActivations();
                loadActivationHistory();
            }, 1500);
        } else {
            // Code généré mais WhatsApp non connecté - afficher le code quand même
            if (result.code) {
                btn.classList.remove('btn--loading');
                btn.classList.add('btn--warning');
                btn.innerHTML = '<i class="fas fa-key"></i><span>Code généré</span>';
                btn.style.background = '';
                alert(`${result.message}\n\nCode: ${result.code}\n\nCommuniquez ce code au marchand manuellement.`);
                setTimeout(() => {
                    loadPendingActivations();
                    loadActivationHistory();
                }, 1500);
            } else {
                throw new Error(result.message || 'Erreur inconnue');
            }
        }

    } catch (error) {
        console.error('Erreur envoi code:', error);
        btn.classList.remove('btn--loading');
        btn.classList.add('btn--error');
        btn.innerHTML = '<i class="fas fa-triangle-exclamation"></i><span>Erreur</span>';
        btn.style.background = '';
        alert(`Erreur: ${error.message}`);

        setTimeout(() => {
            btn.innerHTML = originalHtml;
            btn.style.background = '';
            btn.classList.remove('btn--loading', 'btn--success', 'btn--warning', 'btn--error');
            btn.disabled = false;
        }, 2000);
    }
}

async function loadActivationHistory() {
    try {
        const data = await apiGet('/api/admin/activation-history?limit=20');
        const container = document.getElementById('activation-history-list');

        if (data.history.length === 0) {
            container.innerHTML = '<div class="hist-empty"><i class="fas fa-inbox"></i><p>Aucun historique d\'activation</p></div>';
            return;
        }

        container.innerHTML = data.history.map((h, i) => {
            const statusIcon = h.status === 'used' ? 'fa-circle-check' : h.status === 'expired' ? 'fa-circle-xmark' : 'fa-clock';
            const adminInitial = (h.admin_email || 'S').charAt(0).toUpperCase();
            const dt = formatDateTime(h.created_at);
            const [datePart, timePart] = dt.includes(' ') ? dt.split(' ') : [dt, ''];
            return `
            <div class="hist-entry ${h.status}" style="animation-delay:${i * 0.06}s">
                <div class="hist-timeline">
                    <div class="hist-ts">
                        <span class="hist-ts-date">${datePart}</span>
                        <span class="hist-ts-time">${timePart}</span>
                    </div>
                    <div class="hist-dot ${h.status}"></div>
                </div>
                <div class="hist-body">
                    <div class="hist-body-top">
                        <span class="hist-name">${h.merchant_name || 'N/A'}</span>
                        <span class="hist-badge ${h.status}"><i class="fas ${statusIcon}"></i>${getStatusLabel(h.status)}</span>
                    </div>
                    <div class="hist-body-bottom">
                        <span class="hist-code">${h.code}</span>
                        <span class="hist-phone"><i class="fas fa-phone-alt"></i>${formatPhone(h.merchant_phone)}</span>
                        <span class="hist-sep">·</span>
                        <span class="hist-admin-chip">
                            <span class="hist-admin-init">${adminInitial}</span>
                            <span class="hist-admin-label">${h.admin_email || 'Système'}</span>
                        </span>
                    </div>
                </div>
            </div>`;
        }).join('');

    } catch (error) {
        console.error('Erreur chargement historique:', error);
    }
}

function getStatusLabel(status) {
    const labels = {
        'pending': 'En attente',
        'used': 'Utilise',
        'expired': 'Expire'
    };
    return labels[status] || status;
}

function formatPhone(phone) {
    if (!phone) return 'N/A';
    // Format: +225 07 XX XX XX
    if (phone.length >= 10) {
        const country = phone.slice(0, 3);
        const rest = phone.slice(3);
        return `+${country} ${rest.replace(/(.{2})/g, '$1 ').trim()}`;
    }
    return phone;
}
