/**
 * KALGA Admin Dashboard - JavaScript
 */

const API_URL = 'http://localhost:8001';

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

async function loadDashboardStats() {
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
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Aucun abonnement expirant prochainement</td></tr>';
        return;
    }

    tbody.innerHTML = subscriptions.map(s => {
        const expiresAt = s.trial_ends_at || s.end_date;
        const expiresDate = new Date(expiresAt).toLocaleDateString('fr-FR');

        return `
            <tr>
                <td>
                    <strong>${s.name}</strong>
                    <br><small style="color: var(--text-muted)">${s.phone}</small>
                </td>
                <td><span class="status-badge ${s.plan}">${s.plan}</span></td>
                <td>${expiresDate}</td>
                <td>
                    <button onclick="openSubscriptionModal(${s.merchant_id})" class="btn btn-small btn-secondary">
                        Modifier
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ============================================
// MERCHANTS
// ============================================

async function loadMerchants() {
    try {
        const filter = document.getElementById('merchant-filter').value;
        const data = await apiGet(`/api/admin/merchants?page=${state.merchantsPage}&limit=20&status_filter=${filter}`);

        renderMerchantsList(data.merchants);
        renderPagination(data.page, data.pages, 'merchants');

    } catch (error) {
        console.error('Erreur chargement marchands:', error);
    }
}

function renderMerchantsList(merchants) {
    const tbody = document.getElementById('merchants-list');

    if (!merchants.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Aucun marchand trouve</td></tr>';
        return;
    }

    tbody.innerHTML = merchants.map(m => {
        const waStatus = m.whatsapp_status === 'ready' ? 'connected' : 'disconnected';
        const waLabel = m.whatsapp_status === 'ready' ? 'Connecte' : 'Deconnecte';
        const userStatus = m.is_active ? 'active' : 'inactive';
        const userLabel = m.is_active ? 'Actif' : 'Inactif';

        return `
            <tr>
                <td>
                    <strong>${m.name || 'N/A'}</strong>
                    <br><small style="color: var(--text-muted)">${m.business_name || ''}</small>
                </td>
                <td>${m.phone || 'N/A'}</td>
                <td><span class="status-badge ${waStatus}">${waLabel}</span></td>
                <td><span class="status-badge ${m.plan || 'trial'}">${m.plan || 'trial'}</span></td>
                <td>${m.messages_used || 0} / ${m.messages_limit || 500}</td>
                <td><span class="status-badge ${userStatus}">${userLabel}</span></td>
                <td>
                    <button onclick="showMerchantDetail(${m.merchant_id})" class="btn btn-small btn-secondary">
                        Details
                    </button>
                </td>
            </tr>
        `;
    }).join('');
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
                            ${data.whatsapp_status === 'ready' ? 'Connecte' : 'Deconnecte'}
                        </span>
                    </div>
                </div>

                <div class="detail-section">
                    <h4>Abonnement</h4>
                    ${data.subscription ? `
                        <div class="detail-row">
                            <span class="detail-label">Plan</span>
                            <span class="status-badge ${data.subscription.plan}">${data.subscription.plan}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Status</span>
                            <span class="status-badge ${data.subscription.status}">${data.subscription.status}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Messages</span>
                            <span class="detail-value">${data.subscription.messages_used} / ${data.subscription.messages_limit}</span>
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
    try {
        const data = await apiGet('/api/admin/system/whatsapp-status');

        document.getElementById('wa-connected').textContent = data.connected;
        document.getElementById('wa-disconnected').textContent = data.disconnected;

        const grid = document.getElementById('whatsapp-grid');
        grid.innerHTML = data.statuses.map(s => {
            const statusClass = s.ready ? 'connected' : 'disconnected';
            const icon = s.ready ? '&#9989;' : '&#10060;';

            return `
                <div class="wa-card ${statusClass}">
                    <div class="wa-card-icon">${icon}</div>
                    <div class="wa-card-info">
                        <div class="wa-card-name">${s.name}</div>
                        <div class="wa-card-phone">${s.phone}</div>
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
    try {
        const data = await apiGet('/api/admin/audit-logs?limit=50');

        const tbody = document.getElementById('audit-list');

        if (!data.logs.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Aucun log</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.map(log => `
            <tr>
                <td>${formatDateTime(log.created_at)}</td>
                <td>${log.admin_email}</td>
                <td>${formatAction(log.action)}</td>
                <td><small style="color: var(--text-muted)">${log.details || ''}</small></td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Erreur chargement logs:', error);
    }
}

function formatAction(action) {
    const actions = {
        'merchant_status_update': 'Modification statut marchand',
        'subscription_update': 'Modification abonnement',
        'admin_created': 'Creation administrateur',
        'system_cleanup': 'Nettoyage systeme'
    };
    return actions[action] || action;
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
    try {
        const data = await apiGet('/api/admin/pending-activations');
        const container = document.getElementById('pending-activations-list');
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
