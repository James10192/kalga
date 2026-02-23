// === KALGA Dashboard - Enhanced JavaScript ===

// Configuration
const CONFIG = {
    KALGA_API: 'http://localhost:8001',
    WHATSAPP_BRIDGE: 'http://localhost:3001',
    REFRESH_INTERVAL: 30000,
    STATUS_CHECK_INTERVAL: 3000
};

// Global State
const state = {
    merchant: null,
    merchantId: null,
    merchantData: null,
    products: [],
    conversations: [],
    pendingSales: [],
    lastPendingCount: 0,
    selectedConversation: null,
    currentFilter: 'active',
    statusCheckInterval: null,
    refreshInterval: null,
    notificationSound: null,
    pendingLocation: { lat: null, lng: null }
};

// === THEME TOGGLE (dark / light) ===
function initTheme() {
    const saved = localStorage.getItem('kalga_theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('kalga_theme', next);
}

// === INITIALIZATION ===
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebarCollapse();
    initNavigation();
    initFilterTabs();
    initNotificationSound();
    checkSavedSession();
    loadMerchantsCount();
});

async function loadMerchantsCount() {
    const el = document.getElementById('stat-merchants');
    if (!el) return;
    try {
        const res = await fetch(`${CONFIG.KALGA_API}/api/merchants/?limit=1`);
        if (!res.ok) return;
        const data = await res.json();
        const count = data.total ?? 0;
        if (count === 0) {
            el.textContent = '0';
        } else if (count >= 1000) {
            el.textContent = Math.floor(count / 1000) + 'k+';
        } else {
            el.textContent = count + '+';
        }
    } catch {
        el.textContent = '—';
    }
}


// Initialiser le son de notification
function initNotificationSound() {
    // Créer un son de notification simple avec Web Audio API
    state.notificationSound = {
        play: function() {
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);

                oscillator.frequency.value = 800;
                oscillator.type = 'sine';
                gainNode.gain.value = 0.3;

                oscillator.start();

                // Jouer 3 bips courts
                setTimeout(() => { gainNode.gain.value = 0; }, 150);
                setTimeout(() => { gainNode.gain.value = 0.3; }, 250);
                setTimeout(() => { gainNode.gain.value = 0; }, 400);
                setTimeout(() => { gainNode.gain.value = 0.3; }, 500);
                setTimeout(() => { gainNode.gain.value = 0; }, 650);
                setTimeout(() => { oscillator.stop(); }, 700);
            } catch (e) {
                console.log('Audio notification not supported');
            }
        }
    };
}

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            showSection(section);
        });
    });
}

function initFilterTabs() {
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.currentFilter = tab.dataset.filter;
            loadConversations();
        });
    });
}

function checkSavedSession() {
    const savedPhone = localStorage.getItem('kalga_merchant_phone');
    if (savedPhone) {
        // Ne pas pré-remplir le champ (le numéro stocké est avec indicatif)
        // Juste vérifier si la session existe
        verifyExistingSession(savedPhone);
    }
}

async function verifyExistingSession(phone) {
    try {
        const statusResponse = await fetch(`${CONFIG.WHATSAPP_BRIDGE}/status/${phone}`);
        if (statusResponse.ok) {
            const status = await statusResponse.json();
            if (status.ready) {
                // Vérifier si le vrai numéro diffère
                if (status.realPhone && status.realPhone !== phone) {
                    await loadMerchantData(phone);
                    await correctMerchantPhone(phone, status.realPhone);
                    await loadMerchantData(state.merchant);
                } else {
                    await loadMerchantData(phone);
                }
                showDashboard();
                return;
            }
        }
    } catch (e) {
        console.log('No existing session');
    }
}

// === CONNECTION ===
async function initConnection() {
    const countryCode = document.getElementById('login-country').value;
    let phoneInput = document.getElementById('login-phone').value.trim();
    const statusDiv = document.getElementById('login-status');

    if (!phoneInput) {
        showLoginStatus('Veuillez entrer un numéro WhatsApp', 'error');
        return;
    }

    // Nettoyer le numéro (enlever espaces, tirets, etc.)
    phoneInput = phoneInput.replace(/[\s\-\+\(\)]/g, '');

    // Si le numéro commence par 0, l'enlever
    if (phoneInput.startsWith('0')) {
        phoneInput = phoneInput.substring(1);
    }

    // Vérifier que c'est bien des chiffres (8-12 chiffres sans indicatif)
    if (!/^\d{8,12}$/.test(phoneInput)) {
        showLoginStatus('Numéro invalide. Entrez 8-12 chiffres.', 'error');
        return;
    }

    // Construire le numéro complet avec l'indicatif
    const phone = countryCode + phoneInput;

    showLoginStatus('Connexion en cours...', 'loading');

    try {
        // Check/Create merchant
        let merchant = await getMerchant(phone);
        if (!merchant) {
            merchant = await createMerchant(phone);
        }

        if (!merchant) {
            showLoginStatus('Erreur lors de la création du marchand', 'error');
            return;
        }

        // Utiliser le numéro normalisé retourné par l'API
        const normalizedPhone = merchant.phone;
        state.merchant = normalizedPhone;
        state.merchantId = merchant.id;
        localStorage.setItem('kalga_merchant_phone', normalizedPhone);

        // Connect WhatsApp avec le numéro normalisé
        const waResponse = await fetch(`${CONFIG.WHATSAPP_BRIDGE}/connect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ merchant_phone: normalizedPhone })
        });

        if (waResponse.ok) {
            const waStatus = await waResponse.json();

            if (waStatus.status && waStatus.status.ready) {
                showLoginStatus('Connecté avec succès!', 'success');
                setTimeout(() => showDashboard(), 1000);
            } else {
                showQRCode(normalizedPhone);
            }
        } else {
            showLoginStatus('Erreur de connexion au bridge WhatsApp', 'error');
        }

    } catch (error) {
        console.error('Connection error:', error);
        showLoginStatus('Erreur: ' + error.message, 'error');
    }
}

async function getMerchant(phone) {
    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${phone}`);
        if (response.ok) {
            return await response.json();
        }
    } catch (e) {}
    return null;
}

async function createMerchant(phone) {
    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: 'Marchand ' + phone.slice(-4),
                phone: phone
            })
        });
        if (response.ok) {
            const data = await response.json();
            return data.merchant;
        }
    } catch (e) {}
    return null;
}

function showQRCode(phone) {
    const qrContainer = document.getElementById('qr-container');
    const qrFrameContainer = document.getElementById('qr-frame-container');
    const qrLoading = document.getElementById('qr-loading');

    qrContainer.style.display = 'block';
    qrLoading.style.display = 'flex';
    qrFrameContainer.innerHTML = '';

    const iframe = document.createElement('iframe');
    iframe.src = `${CONFIG.WHATSAPP_BRIDGE}/qr/${phone}`;
    iframe.onload = () => {
        qrLoading.style.display = 'none';
    };
    qrFrameContainer.appendChild(iframe);

    showLoginStatus('Scannez le QR code avec WhatsApp', 'loading');

    // Start checking connection status
    startStatusCheck(phone);
}

function startStatusCheck(phone) {
    if (state.statusCheckInterval) {
        clearInterval(state.statusCheckInterval);
    }

    state.statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch(`${CONFIG.WHATSAPP_BRIDGE}/status/${phone}`);
            if (response.ok) {
                const status = await response.json();
                if (status.ready) {
                    clearInterval(state.statusCheckInterval);

                    // Log le vrai numéro WhatsApp si différent (info seulement, pas de correction en base)
                    if (status.realPhone && status.realPhone !== phone) {
                        console.log(`Numéro WhatsApp réel: ${status.realPhone} (saisi: ${phone})`);
                    }
                    showLoginStatus('WhatsApp connecté!', 'success');

                    // Vérifier l'abonnement avant d'afficher le dashboard
                    setTimeout(() => checkSubscriptionAndProceed(), 1000);
                }
            }
        } catch (e) {
            console.log('Status check failed');
        }
    }, CONFIG.STATUS_CHECK_INTERVAL);
}

/**
 * Corrige le numéro du marchand si le vrai WhatsApp diffère du numéro saisi.
 * Met à jour le marchand dans l'API et le state local.
 */
async function correctMerchantPhone(oldPhone, realPhone) {
    try {
        // Mettre à jour le numéro du marchand dans l'API
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}/phone`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: realPhone })
        });

        if (response.ok) {
            // Mettre à jour le state local
            state.merchant = realPhone;
            localStorage.setItem('kalga_merchant_phone', realPhone);
            console.log('Numéro marchand corrigé avec succès');
        } else {
            console.error('Erreur correction numéro:', await response.text());
        }
    } catch (error) {
        console.error('Erreur correction numéro:', error);
    }
}

// === SUBSCRIPTION & ACTIVATION ===
async function checkSubscriptionAndProceed() {
    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/activation/status/${state.merchant}`);
        if (response.ok) {
            const data = await response.json();

            if (data.is_active) {
                // Abonnement actif - continuer vers le dashboard
                showDashboard();
            } else {
                // Pas d'abonnement actif - afficher l'écran de paiement
                showPaymentScreen();
            }
        } else {
            // Erreur API - afficher l'écran de paiement par défaut
            showPaymentScreen();
        }
    } catch (error) {
        console.error('Subscription check error:', error);
        // En cas d'erreur, afficher l'écran de paiement
        showPaymentScreen();
    }
}

function showPaymentScreen() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('payment-screen').style.display = 'flex';
    document.getElementById('activation-screen').style.display = 'none';
    document.getElementById('location-screen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'none';

    // Initialiser les méthodes de paiement cliquables
    initPaymentMethods();
}

function showActivationCodeScreen() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('payment-screen').style.display = 'none';
    document.getElementById('activation-screen').style.display = 'flex';
    document.getElementById('location-screen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'none';

    // Focus sur le champ de code
    setTimeout(() => {
        document.getElementById('activation-code').focus();
    }, 100);
}

function initPaymentMethods() {
    document.querySelectorAll('.payment-method').forEach(method => {
        method.addEventListener('click', () => {
            // Désélectionner tous
            document.querySelectorAll('.payment-method').forEach(m => m.classList.remove('selected'));
            // Sélectionner celui-ci
            method.classList.add('selected');
        });
    });
}

async function verifyActivationCode() {
    const codeInput = document.getElementById('activation-code');
    const code = codeInput.value.trim().toUpperCase();
    const statusDiv = document.getElementById('activation-status');
    const btn = document.getElementById('btn-verify-code');

    if (!code || code.length < 8) {
        statusDiv.textContent = 'Veuillez entrer un code valide (8 caractères)';
        statusDiv.className = 'activation-status error';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Vérification...';
    statusDiv.textContent = 'Vérification en cours...';
    statusDiv.className = 'activation-status loading';

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/activation/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: code,
                merchant_phone: state.merchant
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            statusDiv.textContent = data.message || 'Compte activé avec succès!';
            statusDiv.className = 'activation-status success';

            // Attendre un peu puis continuer vers le dashboard
            setTimeout(() => {
                showDashboard();
            }, 1500);
        } else {
            statusDiv.textContent = data.detail || data.message || 'Code invalide';
            statusDiv.className = 'activation-status error';
        }
    } catch (error) {
        console.error('Activation error:', error);
        statusDiv.textContent = 'Erreur de connexion. Réessayez.';
        statusDiv.className = 'activation-status error';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Activer mon compte';
    }
}

function showLoginStatus(message, type) {
    const statusDiv = document.getElementById('login-status');
    statusDiv.textContent = message;
    statusDiv.className = 'login-status ' + type;
}

// === DASHBOARD ===
async function showDashboard() {
    // Vérifier si le marchand a une localisation configurée
    const merchant = await getMerchant(state.merchant);
    state.merchantData = merchant;
    state.merchantId = merchant.id;

    if (!merchant.address && !merchant.latitude) {
        // Pas de localisation - afficher l'écran de configuration
        showLocationScreen();
        return;
    }

    // Localisation OK - afficher le dashboard
    displayMainDashboard();
}

function displayMainDashboard() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('payment-screen').style.display = 'none';
    document.getElementById('activation-screen').style.display = 'none';
    document.getElementById('location-screen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'flex';

    // Update merchant info in sidebar
    const merchantName = state.merchantData?.business_name || state.merchantData?.name || 'Marchand ' + state.merchant.slice(-4);
    document.getElementById('sidebar-merchant-name').textContent = merchantName;
    document.getElementById('sidebar-merchant-phone').textContent = formatPhone(state.merchant);
    document.getElementById('settings-phone').value = state.merchant;

    // Set storefront link (utilise l'URL de l'API, pas file://)
    const storefrontUrl = `${CONFIG.KALGA_API}/boutique/boutique.html?m=${state.merchant}`;
    const storefrontInput = document.getElementById('storefront-url');
    if (storefrontInput) {
        storefrontInput.value = storefrontUrl;
    }

    // Load data
    refreshData();

    // Start periodic refresh
    startPeriodicRefresh();
}

// === STOREFRONT LINK ===
function copyStorefrontLink() {
    const input = document.getElementById('storefront-url');
    const feedback = document.getElementById('storefront-copy-feedback');
    if (!input) return;

    navigator.clipboard.writeText(input.value).then(() => {
        feedback.style.display = 'block';
        setTimeout(() => { feedback.style.display = 'none'; }, 3000);
    }).catch(() => {
        // Fallback pour navigateurs anciens
        input.select();
        document.execCommand('copy');
        feedback.style.display = 'block';
        setTimeout(() => { feedback.style.display = 'none'; }, 3000);
    });
}

function openStorefrontLink() {
    const input = document.getElementById('storefront-url');
    if (input) {
        window.open(input.value, '_blank');
    }
}

function showLocationScreen() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('payment-screen').style.display = 'none';
    document.getElementById('activation-screen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('location-screen').style.display = 'flex';

    // Reset form
    document.getElementById('location-address').value = '';
    document.getElementById('location-lat').value = '';
    document.getElementById('location-lng').value = '';
    document.getElementById('gps-coords').style.display = 'none';
    document.getElementById('gps-status').textContent = '';
    state.pendingLocation = { lat: null, lng: null };
}

// === LOCATION FUNCTIONS ===
function getGPSLocation() {
    const btn = document.getElementById('btn-get-gps');
    const statusDiv = document.getElementById('gps-status');
    const coordsDiv = document.getElementById('gps-coords');

    if (!navigator.geolocation) {
        statusDiv.textContent = 'La géolocalisation n\'est pas supportée par ce navigateur';
        statusDiv.className = 'gps-status error';
        return;
    }

    btn.disabled = true;
    btn.classList.add('loading');
    btn.innerHTML = '<i class="fas fa-spinner"></i> Localisation en cours...';
    statusDiv.textContent = 'Recherche de votre position...';
    statusDiv.className = 'gps-status';

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            state.pendingLocation = { lat, lng };
            document.getElementById('location-lat').value = lat;
            document.getElementById('location-lng').value = lng;

            coordsDiv.style.display = 'block';
            document.getElementById('gps-coords-display').textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;

            statusDiv.textContent = 'Position détectée avec succès!';
            statusDiv.className = 'gps-status success';

            btn.disabled = false;
            btn.classList.remove('loading');
            btn.innerHTML = '<i class="fas fa-check"></i> Position détectée';
            btn.style.background = 'var(--success)';
            btn.style.borderColor = 'var(--success)';
            btn.style.color = 'white';
        },
        (error) => {
            let errorMsg = 'Impossible d\'obtenir votre position';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMsg = 'Accès à la position refusé. Autorisez la géolocalisation dans votre navigateur.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMsg = 'Position non disponible. Vérifiez votre GPS.';
                    break;
                case error.TIMEOUT:
                    errorMsg = 'Délai dépassé. Réessayez.';
                    break;
            }

            statusDiv.textContent = errorMsg;
            statusDiv.className = 'gps-status error';

            btn.disabled = false;
            btn.classList.remove('loading');
            btn.innerHTML = '<i class="fas fa-crosshairs"></i> Réessayer';
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

async function saveLocation() {
    const address = document.getElementById('location-address').value.trim();
    // Priorite: champs manuels > GPS auto-detecte
    const manualLat = parseFloat(document.getElementById('location-lat').value);
    const manualLng = parseFloat(document.getElementById('location-lng').value);
    const lat = (!isNaN(manualLat)) ? manualLat : (state.pendingLocation ? state.pendingLocation.lat : null);
    const lng = (!isNaN(manualLng)) ? manualLng : (state.pendingLocation ? state.pendingLocation.lng : null);

    if (!address) {
        showToast('Veuillez entrer l\'adresse de votre boutique', 'error');
        return;
    }

    const btn = document.getElementById('btn-save-location');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}/location`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                address: address,
                latitude: lat,
                longitude: lng
            })
        });

        if (response.ok) {
            showToast('Localisation enregistrée!', 'success');
            // Recharger les données du marchand
            state.merchantData = await getMerchant(state.merchant);
            // Afficher le dashboard
            displayMainDashboard();
        } else {
            const error = await response.json();
            showToast('Erreur: ' + (error.detail || 'Impossible d\'enregistrer'), 'error');
        }
    } catch (error) {
        showToast('Erreur de connexion: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Continuer';
    }
}

// === SETTINGS LOCATION FUNCTIONS ===
function getSettingsGPS() {
    const statusSpan = document.getElementById('settings-gps-status');

    if (!navigator.geolocation) {
        statusSpan.textContent = 'GPS non supporté';
        statusSpan.className = 'gps-mini-status error';
        return;
    }

    statusSpan.textContent = 'Recherche...';
    statusSpan.className = 'gps-mini-status loading';

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            document.getElementById('settings-lat').value = lat;
            document.getElementById('settings-lng').value = lng;

            statusSpan.textContent = `✓ Position: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            statusSpan.className = 'gps-mini-status success';
        },
        (error) => {
            statusSpan.textContent = 'Erreur GPS: ' + error.message;
            statusSpan.className = 'gps-mini-status error';
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

async function updateLocation() {
    const address = document.getElementById('settings-address').value.trim();
    const lat = parseFloat(document.getElementById('settings-lat').value) || null;
    const lng = parseFloat(document.getElementById('settings-lng').value) || null;

    if (!address && !lat) {
        showToast('Veuillez entrer une adresse ou obtenir votre position GPS', 'error');
        return;
    }

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}/location`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                address: address || null,
                latitude: lat,
                longitude: lng
            })
        });

        if (response.ok) {
            showToast('Localisation mise à jour!', 'success');
            state.merchantData = await getMerchant(state.merchant);
        } else {
            const error = await response.json();
            showToast('Erreur: ' + (error.detail || 'Impossible de mettre à jour'), 'error');
        }
    } catch (error) {
        showToast('Erreur de connexion: ' + error.message, 'error');
    }
}

function loadSettingsLocation() {
    if (state.merchantData) {
        document.getElementById('settings-address').value = state.merchantData.address || '';
        document.getElementById('settings-lat').value = state.merchantData.latitude || '';
        document.getElementById('settings-lng').value = state.merchantData.longitude || '';

        const statusSpan = document.getElementById('settings-gps-status');
        if (state.merchantData.latitude && state.merchantData.longitude) {
            statusSpan.textContent = `✓ ${state.merchantData.latitude.toFixed(4)}, ${state.merchantData.longitude.toFixed(4)}`;
            statusSpan.className = 'gps-mini-status success';
        } else {
            statusSpan.textContent = 'Non configuré';
            statusSpan.className = 'gps-mini-status';
        }
    }
}

function startPeriodicRefresh() {
    if (state.refreshInterval) {
        clearInterval(state.refreshInterval);
    }
    state.refreshInterval = setInterval(refreshData, CONFIG.REFRESH_INTERVAL);
}

async function refreshData() {
    await Promise.all([
        loadProducts(),
        loadConversations(),
        loadPendingSales(),
        loadStats()
    ]);
}

async function loadMerchantData(phone) {
    const merchant = await getMerchant(phone);
    if (merchant) {
        state.merchant = phone;
        state.merchantId = merchant.id;
        state.merchantData = merchant;
    }
}

function showSection(sectionName) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === sectionName) {
            item.classList.add('active');
        }
    });

    // Update sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`section-${sectionName}`).classList.add('active');

    // Update page title
    const titles = {
        overview: 'Aperçu',
        products: 'Produits',
        conversations: 'Conversations',
        statistics: 'Statistiques',
        settings: 'Paramètres'
    };
    document.getElementById('page-title').textContent = titles[sectionName] || sectionName;

    // Charger les données spécifiques à la section
    if (sectionName === 'statistics') {
        loadStatistics(currentStatsPeriod);
    }

    if (sectionName === 'settings') {
        loadSettingsLocation();
        loadStorefrontSettings();
    }
}

function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
}

function toggleSidebarCollapse() {
    const sidebar = document.querySelector('.sidebar');
    const dashboard = document.querySelector('.dashboard');
    const isCollapsed = sidebar.classList.toggle('collapsed');
    dashboard.classList.toggle('sidebar-collapsed', isCollapsed);
    localStorage.setItem('kalga_sidebar_collapsed', isCollapsed ? '1' : '0');
}

function initSidebarCollapse() {
    if (localStorage.getItem('kalga_sidebar_collapsed') === '1') {
        document.querySelector('.sidebar')?.classList.add('collapsed');
        document.querySelector('.dashboard')?.classList.add('sidebar-collapsed');
    }
}

// === PRODUCTS ===
async function loadProducts() {
    if (!state.merchantId) return;

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}/products`);
        if (response.ok) {
            const data = await response.json();
            state.products = data.products || [];
            renderProducts();
            renderTopProducts();
            updateStats();
        }
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

function renderProducts() {
    const grid = document.getElementById('products-grid');

    if (state.products.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <i class="fas fa-box-open"></i>
                <p>Aucun produit pour le moment</p>
                <button class="btn-primary" onclick="showAddProductModal()" style="margin-top: 20px;">
                    <i class="fas fa-plus"></i> Ajouter un produit
                </button>
            </div>
        `;
        return;
    }

    // Grouper les produits par group_id
    const grouped = [];
    const seenGroups = new Set();

    for (const p of state.products) {
        if (p.group_id) {
            if (seenGroups.has(p.group_id)) continue;
            seenGroups.add(p.group_id);
            const variants = state.products.filter(x => x.group_id === p.group_id);
            const main = variants.find(x => !x.variant_name) || variants[0];
            grouped.push({ ...main, _variants: variants });
        } else {
            grouped.push({ ...p, _variants: [p] });
        }
    }

    grid.innerHTML = grouped.map(product => {
        const stockQty = product.stock_quantity;
        const isUnlimited = stockQty === -1 || stockQty === null;
        const isLow = !isUnlimited && stockQty <= (product.low_stock_threshold || 5) && stockQty > 0;
        const isOut = !isUnlimited && stockQty === 0;

        let stockBadge = '';
        if (isOut) {
            stockBadge = '<span class="stock-badge out">Rupture</span>';
        } else if (isLow) {
            stockBadge = `<span class="stock-badge low">${stockQty} restants</span>`;
        } else if (!isUnlimited) {
            stockBadge = `<span class="stock-badge ok">${stockQty} en stock</span>`;
        }

        // Afficher les variantes si le produit en a
        const hasVariants = product._variants.length > 1;
        const variantsHtml = hasVariants ? `
            <div class="product-variants-list">
                <div class="variants-label"><i class="fas fa-palette"></i> ${product._variants.length} variantes:</div>
                ${product._variants.map(v => `
                    <span class="variant-chip" title="${v.code}">
                        ${escapeHtml(v.variant_name || 'Principal')}
                        <small>${v.code}</small>
                    </span>
                `).join('')}
            </div>
        ` : '';

        // Nom affiché: nom du produit principal (sans le variant_name)
        const displayName = product._variants.length > 1
            ? (product._variants.find(v => !v.variant_name)?.name || product.name.replace(/ - .+$/, ''))
            : product.name;

        return `
        <div class="product-card ${isOut ? 'out-of-stock' : ''}">
            <div class="product-card-header">
                <h4>${escapeHtml(displayName)}</h4>
                <span class="product-code-badge">${product.code}</span>
            </div>
            ${stockBadge}
            ${product.description ? `<p class="product-description">${escapeHtml(product.description)}</p>` : ''}
            ${variantsHtml}
            <div class="product-prices">
                <div class="price-item">
                    <span class="price-label">Prix affiché</span>
                    <span class="price-value">${formatPrice(product.price)} F</span>
                </div>
                <div class="price-item">
                    <span class="price-label">Prix minimum</span>
                    <span class="price-value min">${formatPrice(product.min_price)} F</span>
                </div>
            </div>
            <div class="product-card-actions">
                <button class="btn-icon" onclick="showStockModal(${product.id}, '${product.code}', ${stockQty})" title="Gérer le stock">
                    <i class="fas fa-boxes"></i>
                </button>
                <button class="btn-icon" onclick="copyCode('${product.code}')" title="Copier le code">
                    <i class="fas fa-copy"></i>
                </button>
                <button class="btn-icon danger" onclick="deleteProduct(${product.id})" title="Supprimer">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
    }).join('');
}

function renderTopProducts() {
    const container = document.getElementById('top-products-list');

    if (state.products.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box"></i>
                <p>Aucun produit</p>
            </div>
        `;
        return;
    }

    // Grouper avant affichage
    const grouped = [];
    const seenGroups = new Set();
    for (const p of state.products) {
        if (p.group_id) {
            if (seenGroups.has(p.group_id)) continue;
            seenGroups.add(p.group_id);
            const main = state.products.filter(x => x.group_id === p.group_id).find(x => !x.variant_name) || p;
            grouped.push(main);
        } else {
            grouped.push(p);
        }
    }

    // Show first 5 products
    const topProducts = grouped.slice(0, 5);
    container.innerHTML = topProducts.map((product, index) => `
        <div class="top-product-item">
            <div class="top-product-rank">${index + 1}</div>
            <div class="top-product-info">
                <div class="top-product-name">${escapeHtml(product.name)}</div>
                <div class="top-product-code">${product.code}</div>
            </div>
            <div class="top-product-price">${formatPrice(product.price)} F</div>
        </div>
    `).join('');
}

function showAddProductModal() {
    document.getElementById('product-name').value = '';
    document.getElementById('product-price').value = '';
    document.getElementById('product-min-price').value = '';
    document.getElementById('product-description').value = '';
    openModal('modal-product');
}

async function createProduct() {
    const name = document.getElementById('product-name').value.trim();
    const price = parseFloat(document.getElementById('product-price').value);
    const minPrice = parseFloat(document.getElementById('product-min-price').value);
    const description = document.getElementById('product-description').value.trim();

    if (!name || !price || !minPrice) {
        showToast('Remplissez tous les champs obligatoires', 'error');
        return;
    }

    if (minPrice > price) {
        showToast('Le prix minimum ne peut pas dépasser le prix affiché', 'error');
        return;
    }

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/products/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                merchant_id: state.merchantId,
                name: name,
                price: price,
                min_price: minPrice,
                description: description || null
            })
        });

        if (response.ok) {
            const data = await response.json();
            closeModal('modal-product');

            // Show success modal with code
            document.getElementById('new-product-code').textContent = data.product.code;
            openModal('modal-code');

            await loadProducts();
            showToast('Produit créé avec succès!', 'success');
        } else {
            const error = await response.json();
            showToast('Erreur: ' + error.detail, 'error');
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

async function deleteProduct(productId) {
    if (!confirm('Voulez-vous vraiment supprimer ce produit?')) return;

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/products/${productId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('Produit supprimé', 'success');
            await loadProducts();
        } else {
            showToast('Erreur lors de la suppression', 'error');
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

function copyCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        showToast('Code copié: ' + code, 'success');
    });
}

function copyProductCode() {
    const code = document.getElementById('new-product-code').textContent;
    navigator.clipboard.writeText(code).then(() => {
        showToast('Code copié!', 'success');
    });
}

// === CONVERSATIONS ===
async function loadConversations() {
    if (!state.merchant) return;

    try {
        let url = `${CONFIG.KALGA_API}/api/chat/conversations/${state.merchant}?status=${state.currentFilter}`;

        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            state.conversations = data.conversations || [];
            renderConversations();
            renderRecentConversations();
            updateStats();
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

function renderConversations() {
    const container = document.getElementById('conversations-list');

    if (state.conversations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comments"></i>
                <p>Aucune conversation ${state.currentFilter === 'active' ? 'active' : ''}</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.conversations.map(conv => `
        <div class="conversation-item ${conv.status === 'completed' ? 'completed' : ''} ${state.selectedConversation?.id === conv.id ? 'active' : ''}"
             onclick="selectConversation(${conv.id})">
            <div class="conversation-item-header">
                <span class="client-name">${formatPhone(conv.client_phone)}</span>
                <span class="conversation-time">${formatTime(conv.updated_at)}</span>
            </div>
            <span class="conversation-product-tag">${conv.product_code} - ${escapeHtml(conv.product_name || '')}</span>
            ${conv.current_offer ? `<div class="conversation-preview">Offre: ${formatPrice(conv.current_offer)} F</div>` : ''}
        </div>
    `).join('');

    // Update badge
    const activeCount = state.conversations.filter(c => c.status === 'active').length;
    document.getElementById('conv-badge').textContent = activeCount;
    document.getElementById('conv-badge').style.display = activeCount > 0 ? 'inline' : 'none';
}

function renderRecentConversations() {
    const container = document.getElementById('recent-conversations-list');

    if (state.conversations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comments"></i>
                <p>Aucune conversation</p>
            </div>
        `;
        return;
    }

    // Show first 5 conversations
    const recent = state.conversations.slice(0, 5);
    container.innerHTML = recent.map(conv => `
        <div class="recent-conv-item" onclick="showSection('conversations'); selectConversation(${conv.id});">
            <div class="recent-conv-avatar">${conv.client_phone.slice(-2)}</div>
            <div class="recent-conv-info">
                <div class="recent-conv-name">${formatPhone(conv.client_phone)}</div>
                <div class="recent-conv-product">${conv.product_code} - ${escapeHtml(conv.product_name || '')}</div>
            </div>
            <div class="recent-conv-time">${formatTime(conv.updated_at)}</div>
        </div>
    `).join('');
}

// === VENTES EN ATTENTE ===
async function loadPendingSales() {
    if (!state.merchant) return;

    try {
        // Charger les conversations en attente (pending_delivery + pending_pickup)
        const response = await fetch(`${CONFIG.KALGA_API}/api/chat/conversations/${state.merchant}?status=pending`);
        if (response.ok) {
            const data = await response.json();
            const pendingSales = data.conversations || [];

            // Vérifier si nouvelles ventes
            if (pendingSales.length > state.lastPendingCount && state.lastPendingCount > 0) {
                // Nouvelle vente! Jouer le son
                playNotificationSound();
                showToast('🚨 Nouvelle vente en attente!', 'warning');
            }

            state.pendingSales = pendingSales;
            state.lastPendingCount = pendingSales.length;
            renderPendingSales();
        }
    } catch (error) {
        console.error('Error loading pending sales:', error);
    }
}

function renderPendingSales() {
    const section = document.getElementById('pending-sales-section');
    const container = document.getElementById('pending-sales-list');
    const countBadge = document.getElementById('pending-count');

    if (state.pendingSales.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    countBadge.textContent = state.pendingSales.length;

    container.innerHTML = state.pendingSales.map(sale => {
        const isPickup = sale.status === 'pending_pickup';
        const typeIcon = isPickup ? '🏪' : '🚚';
        const typeLabel = isPickup ? 'Récupération' : 'Livraison';
        return `
        <div class="pending-sale-item">
            <div class="pending-sale-info">
                <div class="pending-sale-product">${escapeHtml(sale.product_name || 'Produit')} (${sale.product_code})</div>
                <div class="pending-sale-details">
                    Client: ${formatPhone(sale.client_phone)} -
                    <span class="pending-sale-price">${formatPrice(sale.current_offer || 0)} F</span>
                </div>
                <div class="pending-sale-type">${typeIcon} ${typeLabel}</div>
            </div>
            <div class="pending-sale-actions">
                <a href="tel:${sale.client_phone}" class="btn-call">
                    <i class="fas fa-phone"></i> Appeler
                </a>
                <button class="btn-done" onclick="markSaleCompleted(${sale.id})">
                    <i class="fas fa-check"></i> Fait
                </button>
            </div>
        </div>
    `}).join('');
}

function playNotificationSound() {
    if (state.notificationSound) {
        state.notificationSound.play();
    }
}

async function markSaleCompleted(convId) {
    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/chat/conversations/${convId}/accept`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast('Vente marquée comme complétée!', 'success');
            await loadPendingSales();
            await loadConversations();
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

async function selectConversation(convId) {
    const conv = state.conversations.find(c => c.id === convId);
    if (!conv) return;

    state.selectedConversation = conv;

    // Update UI
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget?.classList.add('active');

    // Load conversation details
    await loadConversationDetail(conv);
}

async function loadConversationDetail(conv) {
    const panel = document.getElementById('conversation-detail');

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/chat/conversations/${conv.id}/messages`);
        let messages = [];
        if (response.ok) {
            const data = await response.json();
            messages = data.messages || [];
        }

        panel.innerHTML = `
            <div class="detail-header">
                <div class="detail-header-info">
                    <h3>${formatPhone(conv.client_phone)}</h3>
                    <span>${conv.product_code} - ${escapeHtml(conv.product_name || '')}</span>
                </div>
                <div class="detail-header-actions">
                    <button class="btn-icon" onclick="closeConversationDetail()" title="Fermer">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="messages-container" id="messages-container">
                ${messages.length === 0 ? '<p style="text-align:center; color:#999;">Aucun message</p>' :
                    messages.map(msg => `
                        <div class="message ${msg.is_from_client ? 'client' : 'bot'}">
                            ${escapeHtml(msg.content)}
                            <div class="message-time">${formatTime(msg.created_at)}</div>
                        </div>
                    `).join('')
                }
            </div>
            <div class="detail-footer">
                ${conv.current_offer ? `
                    <div class="offer-info">
                        <span>Dernière offre client:</span>
                        <span>${formatPrice(conv.current_offer)} FCFA</span>
                    </div>
                ` : ''}
                <div class="manual-actions">
                    <button class="btn-primary" onclick="acceptOffer(${conv.id})">
                        <i class="fas fa-check"></i> Accepter
                    </button>
                    <button class="btn-secondary" onclick="rejectOffer(${conv.id})">
                        <i class="fas fa-times"></i> Refuser
                    </button>
                </div>
            </div>
        `;

        // Scroll to bottom
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Activate panel on mobile
        panel.classList.add('active');

    } catch (error) {
        console.error('Error loading conversation detail:', error);
    }
}

function closeConversationDetail() {
    const panel = document.getElementById('conversation-detail');
    panel.classList.remove('active');
    panel.innerHTML = `
        <div class="empty-detail">
            <i class="fas fa-comments"></i>
            <p>Sélectionnez une conversation</p>
        </div>
    `;
    state.selectedConversation = null;
}

async function acceptOffer(convId) {
    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/chat/conversations/${convId}/accept`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast('Offre acceptée!', 'success');
            await loadConversations();
            closeConversationDetail();
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

async function rejectOffer(convId) {
    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/chat/conversations/${convId}/reject`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast('Offre refusée', 'warning');
            await loadConversations();
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

// === STATS ===
async function loadStats() {
    // Stats are updated from products and conversations
    updateStats();
}

function updateStats() {
    const productCount = state.products.length;
    const activeConversations = state.conversations.filter(c => c.status === 'active').length;
    const completedSales = state.conversations.filter(c => c.status === 'completed').length;

    // Calculate total revenue (sum of final prices for completed sales)
    const totalRevenue = state.conversations
        .filter(c => c.status === 'completed' && c.current_offer)
        .reduce((sum, c) => sum + c.current_offer, 0);

    document.getElementById('stat-products').textContent = productCount;
    document.getElementById('stat-conversations').textContent = activeConversations;
    document.getElementById('stat-sales').textContent = completedSales;
    document.getElementById('stat-revenue').textContent = formatPrice(totalRevenue);
}

// === SETTINGS ===
async function updateMerchant() {
    const name = document.getElementById('settings-name').value.trim();

    if (!name) {
        showToast('Veuillez entrer un nom', 'error');
        return;
    }

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (response.ok) {
            showToast('Profil mis à jour!', 'success');
            document.getElementById('sidebar-merchant-name').textContent = name;
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

// === STOREFRONT PROFILE ===

function loadStorefrontSettings() {
    if (!state.merchantData) return;
    const m = state.merchantData;

    const bizName = document.getElementById('storefront-business-name');
    const tagline = document.getElementById('storefront-tagline');
    const about = document.getElementById('storefront-about');

    if (bizName) bizName.value = m.business_name || '';
    if (tagline) tagline.value = m.tagline || '';
    if (about) about.value = m.about || '';

    // Load banner preview
    const bannerPreview = document.getElementById('storefront-banner-preview');
    if (bannerPreview && m.banner_path) {
        bannerPreview.innerHTML = `<img src="${CONFIG.KALGA_API}/uploads/${m.banner_path}" alt="Bannière">`;
        const removeBtn = document.getElementById('storefront-banner-remove');
        if (removeBtn) removeBtn.style.display = 'inline-flex';
    }

    // Load logo preview
    const logoPreview = document.getElementById('storefront-logo-preview');
    if (logoPreview && m.logo_path) {
        logoPreview.innerHTML = `<img src="${CONFIG.KALGA_API}/uploads/${m.logo_path}" alt="Logo">`;
        const removeBtn = document.getElementById('storefront-logo-remove');
        if (removeBtn) removeBtn.style.display = 'inline-flex';
    }
}

function previewStorefrontImage(input, type) {
    const file = input.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        showToast('Image trop volumineuse (max 5 MB)', 'error');
        input.value = '';
        return;
    }

    const preview = document.getElementById(`storefront-${type}-preview`);
    const removeBtn = document.getElementById(`storefront-${type}-remove`);
    const reader = new FileReader();

    reader.onload = (e) => {
        preview.innerHTML = `<img src="${e.target.result}" alt="${type}">`;
        if (removeBtn) removeBtn.style.display = 'inline-flex';
    };
    reader.readAsDataURL(file);
}

function removeStorefrontImage(type) {
    const preview = document.getElementById(`storefront-${type}-preview`);
    const input = document.getElementById(`storefront-${type}-input`);
    const removeBtn = document.getElementById(`storefront-${type}-remove`);

    const placeholder = type === 'banner'
        ? '<span class="storefront-preview-placeholder"><i class="fas fa-image"></i> Aucune bannière</span>'
        : '<span class="storefront-preview-placeholder"><i class="fas fa-camera"></i> Aucun logo</span>';

    preview.innerHTML = placeholder;
    if (input) input.value = '';
    if (removeBtn) removeBtn.style.display = 'none';
}

async function saveStorefrontProfile() {
    const businessName = document.getElementById('storefront-business-name').value.trim();
    const tagline = document.getElementById('storefront-tagline').value.trim();
    const about = document.getElementById('storefront-about').value.trim();
    const bannerInput = document.getElementById('storefront-banner-input');
    const logoInput = document.getElementById('storefront-logo-input');

    try {
        // 1. Save text fields
        const updateData = {};
        if (businessName) updateData.business_name = businessName;
        if (tagline) updateData.tagline = tagline;
        if (about) updateData.about = about;

        if (Object.keys(updateData).length > 0) {
            await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });
        }

        // 2. Upload banner if selected
        if (bannerInput.files.length > 0) {
            const formData = new FormData();
            formData.append('file', bannerInput.files[0]);
            formData.append('image_type', 'banner');

            await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}/upload-image`, {
                method: 'POST',
                body: formData
            });
        }

        // 3. Upload logo if selected
        if (logoInput.files.length > 0) {
            const formData = new FormData();
            formData.append('file', logoInput.files[0]);
            formData.append('image_type', 'logo');

            await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchantId}/upload-image`, {
                method: 'POST',
                body: formData
            });
        }

        // Refresh merchant data
        const merchant = await getMerchant(state.merchant);
        state.merchantData = merchant;

        showToast('Vitrine mise à jour!', 'success');
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

async function disconnectWhatsApp() {
    if (!confirm('Voulez-vous vraiment déconnecter WhatsApp?')) return;

    try {
        await fetch(`${CONFIG.WHATSAPP_BRIDGE}/disconnect/${state.merchant}`, {
            method: 'POST'
        });
    } catch (e) {}

    logout();
}

function logout() {
    // Clear state
    localStorage.removeItem('kalga_merchant_phone');
    state.merchant = null;
    state.merchantId = null;
    state.products = [];
    state.conversations = [];

    // Clear intervals
    if (state.statusCheckInterval) clearInterval(state.statusCheckInterval);
    if (state.refreshInterval) clearInterval(state.refreshInterval);

    // Show login
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('qr-container').style.display = 'none';
    document.getElementById('login-status').textContent = '';
    document.getElementById('login-status').className = 'login-status';
}

// === MODAL UTILITIES ===
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// === TOAST NOTIFICATIONS ===
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type] || icons.info}"></i>
        <span>${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// === UTILITY FUNCTIONS ===
function formatPrice(price) {
    if (!price) return '0';
    return new Intl.NumberFormat('fr-FR').format(price);
}

function formatPhone(phone) {
    if (!phone) return '';
    // Format as +225 XX XX XX XX XX
    if (phone.length >= 10) {
        const last = phone.slice(-10);
        return `+${phone.slice(0, -10) || '225'} ${last.match(/.{1,2}/g).join(' ')}`;
    }
    return phone;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}min`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h`;
    }

    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}j`;
    }

    // Otherwise show date
    return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// === STATISTICS ===
let dailyChart = null;
let hourlyChart = null;
let currentStatsPeriod = 7;

async function loadStatistics(days = 7) {
    if (!state.merchant) return;

    currentStatsPeriod = days;

    // Update period buttons
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.days) === days);
    });

    try {
        // Load summary stats
        const summaryResponse = await fetch(
            `${CONFIG.KALGA_API}/api/stats/${state.merchant}/summary?days=${days}`
        );
        if (summaryResponse.ok) {
            const summary = await summaryResponse.json();
            document.getElementById('stats-total-conv').textContent = summary.total_conversations || 0;
            document.getElementById('stats-total-sales').textContent = summary.total_sales || 0;
            document.getElementById('stats-total-revenue').textContent = formatPrice(summary.total_revenue || 0) + ' F';
            document.getElementById('stats-conversion-rate').textContent = (summary.conversion_rate || 0) + '%';
        }

        // Load daily stats for chart
        const dailyResponse = await fetch(
            `${CONFIG.KALGA_API}/api/stats/${state.merchant}/daily?days=${days}`
        );
        if (dailyResponse.ok) {
            const daily = await dailyResponse.json();
            renderDailyChart(daily.data);
        }

        // Load hourly activity
        const hourlyResponse = await fetch(
            `${CONFIG.KALGA_API}/api/stats/${state.merchant}/hourly-activity?days=${days}`
        );
        if (hourlyResponse.ok) {
            const hourly = await hourlyResponse.json();
            renderHourlyChart(hourly.data);
        }

        // Load top products
        const topResponse = await fetch(
            `${CONFIG.KALGA_API}/api/stats/${state.merchant}/top-products?limit=5`
        );
        if (topResponse.ok) {
            const top = await topResponse.json();
            renderTopProductsStats(top.products);
        }

    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

function renderDailyChart(data) {
    const ctx = document.getElementById('chart-daily-activity');
    if (!ctx) return;

    // Destroy existing chart
    if (dailyChart) {
        dailyChart.destroy();
    }

    const labels = data.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
    });

    dailyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Conversations',
                    data: data.map(d => d.conversations_count),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Ventes',
                    data: data.map(d => d.sales_count),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function renderHourlyChart(data) {
    const ctx = document.getElementById('chart-hourly-activity');
    if (!ctx) return;

    // Destroy existing chart
    if (hourlyChart) {
        hourlyChart.destroy();
    }

    const labels = data.map(d => `${d.hour}h`);
    const values = data.map(d => d.count);

    hourlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Messages',
                data: values,
                backgroundColor: 'rgba(37, 211, 102, 0.6)',
                borderColor: '#25d366',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function renderTopProductsStats(products) {
    const container = document.getElementById('stats-top-products');
    if (!container) return;

    if (!products || products.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-box"></i>
                <p>Aucune donnée de ventes</p>
            </div>
        `;
        return;
    }

    container.innerHTML = products.map((p, index) => `
        <div class="top-product-stat-item">
            <div class="top-product-stat-rank">${index + 1}</div>
            <div class="top-product-stat-info">
                <div class="top-product-stat-name">${escapeHtml(p.name)}</div>
                <div class="top-product-stat-code">${p.code}</div>
            </div>
            <div class="top-product-stat-metrics">
                <div class="top-product-stat-sales">${p.sales_count || 0} ventes</div>
                <div class="top-product-stat-revenue">${formatPrice(p.revenue || 0)} F</div>
            </div>
        </div>
    `).join('');
}

// Initialize period buttons
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            loadStatistics(parseInt(btn.dataset.days));
        });
    });
});

// === STOCK MANAGEMENT ===
let currentStockProductId = null;
let currentStockProductCode = null;

function showStockModal(productId, productCode, currentStock) {
    currentStockProductId = productId;
    currentStockProductCode = productCode;

    document.getElementById('stock-modal-code').textContent = productCode;
    document.getElementById('stock-quantity').value = currentStock !== null ? currentStock : -1;

    // Find product to get threshold
    const product = state.products.find(p => p.id === productId);
    document.getElementById('stock-threshold').value = product?.low_stock_threshold || 5;

    openModal('modal-stock');
}

function adjustStock(delta) {
    const input = document.getElementById('stock-quantity');
    let current = parseInt(input.value) || 0;

    // Don't go below -1
    if (current + delta >= -1) {
        input.value = current + delta;
    }
}

function setUnlimitedStock() {
    document.getElementById('stock-quantity').value = -1;
}

function setStockValue(value) {
    const input = document.getElementById('stock-quantity');
    const current = parseInt(input.value) || 0;

    // If unlimited (-1), start from 0
    if (current === -1) {
        input.value = value;
    } else {
        input.value = current + value;
    }
}

async function saveStock() {
    const quantity = parseInt(document.getElementById('stock-quantity').value);
    const threshold = parseInt(document.getElementById('stock-threshold').value) || 5;

    if (isNaN(quantity) || quantity < -1) {
        showToast('Quantité invalide', 'error');
        return;
    }

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/products/${currentStockProductCode}/stock`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                quantity: quantity,
                low_stock_threshold: threshold
            })
        });

        if (response.ok) {
            showToast('Stock mis à jour!', 'success');
            closeModal('modal-stock');

            // Reload products to reflect changes
            await loadProducts();
        } else {
            const error = await response.json();
            showToast('Erreur: ' + (error.detail || 'Impossible de mettre à jour'), 'error');
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

// === KEYBOARD SHORTCUTS ===
document.addEventListener('keydown', (e) => {
    // Escape to close modals
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(modal => {
            modal.classList.remove('active');
        });
    }

    // Ctrl+N for new product
    if (e.ctrlKey && e.key === 'n' && state.merchant) {
        e.preventDefault();
        showAddProductModal();
    }
});

// === MODE ABSENCE ===
let awaySettings = {
    away_mode_enabled: false,
    working_hours: null,
    away_message: ''
};

async function loadAwaySettings() {
    if (!state.merchant) return;

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchant}/away-settings`);
        if (response.ok) {
            const data = await response.json();
            awaySettings = data.settings || {
                away_mode_enabled: false,
                working_hours: null,
                away_message: ''
            };

            // Mettre à jour l'UI
            document.getElementById('away-mode-toggle').checked = awaySettings.away_mode_enabled;
            document.getElementById('away-message').value = awaySettings.away_message || '';

            // Mettre à jour l'indicateur de statut
            updateAwayStatusIndicator(data.current_status);

            // Mettre à jour les horaires si configurés
            if (awaySettings.working_hours) {
                document.getElementById('working-hours-enabled').checked = awaySettings.working_hours.enabled;
                loadWorkingHoursToUI(awaySettings.working_hours.schedule);
            }
        }
    } catch (error) {
        console.error('Erreur chargement paramètres absence:', error);
    }
}

function updateAwayStatusIndicator(status) {
    const indicator = document.getElementById('away-status-indicator');
    if (!indicator) return;

    if (status.is_available) {
        indicator.className = 'away-status-indicator available';
        indicator.innerHTML = '<i class="fas fa-circle"></i><span>Vous êtes disponible</span>';
    } else {
        indicator.className = 'away-status-indicator away';
        indicator.innerHTML = '<i class="fas fa-circle"></i><span>Mode absence actif</span>';
    }
}

async function toggleAwayMode(enabled) {
    if (!state.merchant) return;

    try {
        const message = document.getElementById('away-message').value;
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchant}/away-toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                enabled: enabled,
                message: message || null
            })
        });

        if (response.ok) {
            const data = await response.json();
            awaySettings.away_mode_enabled = data.away_mode_enabled;
            updateAwayStatusIndicator(data);
            showToast(enabled ? 'Mode absence activé' : 'Mode absence désactivé', 'success');
        } else {
            showToast('Erreur lors de la mise à jour', 'error');
            // Rétablir l'état du toggle
            document.getElementById('away-mode-toggle').checked = !enabled;
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
        document.getElementById('away-mode-toggle').checked = !enabled;
    }
}

function showWorkingHoursModal() {
    // Charger les paramètres actuels si disponibles
    if (awaySettings.working_hours) {
        document.getElementById('working-hours-enabled').checked = awaySettings.working_hours.enabled;
        loadWorkingHoursToUI(awaySettings.working_hours.schedule);
    }

    // Initialiser les toggles de jours
    initDayToggles();

    openModal('modal-working-hours');
}

function initDayToggles() {
    document.querySelectorAll('.schedule-day').forEach(dayEl => {
        const checkbox = dayEl.querySelector('.day-enabled');
        const timeInputs = dayEl.querySelectorAll('input[type="time"]');

        checkbox.addEventListener('change', () => {
            timeInputs.forEach(input => {
                input.disabled = !checkbox.checked;
            });
            dayEl.classList.toggle('disabled', !checkbox.checked);
        });

        // Initialiser l'état
        if (!checkbox.checked) {
            timeInputs.forEach(input => input.disabled = true);
            dayEl.classList.add('disabled');
        }
    });
}

function loadWorkingHoursToUI(schedule) {
    if (!schedule) return;

    document.querySelectorAll('.schedule-day').forEach(dayEl => {
        const day = dayEl.dataset.day;
        const dayConfig = schedule[day];

        if (dayConfig) {
            const checkbox = dayEl.querySelector('.day-enabled');
            const openInput = dayEl.querySelector('.time-open');
            const closeInput = dayEl.querySelector('.time-close');

            checkbox.checked = dayConfig.enabled !== false;
            openInput.value = dayConfig.open || '08:00';
            closeInput.value = dayConfig.close || '18:00';

            openInput.disabled = !checkbox.checked;
            closeInput.disabled = !checkbox.checked;
            dayEl.classList.toggle('disabled', !checkbox.checked);
        }
    });
}

function getWorkingHoursFromUI() {
    const schedule = {};

    document.querySelectorAll('.schedule-day').forEach(dayEl => {
        const day = dayEl.dataset.day;
        const enabled = dayEl.querySelector('.day-enabled').checked;
        const open = dayEl.querySelector('.time-open').value;
        const close = dayEl.querySelector('.time-close').value;

        schedule[day] = { open, close, enabled };
    });

    return {
        enabled: document.getElementById('working-hours-enabled').checked,
        timezone: 'Africa/Abidjan',
        schedule: schedule
    };
}

async function saveWorkingHours() {
    if (!state.merchant) return;

    const workingHours = getWorkingHoursFromUI();
    const awayMessage = document.getElementById('away-message').value;

    try {
        const response = await fetch(`${CONFIG.KALGA_API}/api/merchants/${state.merchant}/away-settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                working_hours: workingHours,
                away_message: awayMessage || null
            })
        });

        if (response.ok) {
            const data = await response.json();
            awaySettings = data.settings;
            updateAwayStatusIndicator(data.current_status);
            closeModal('modal-working-hours');
            showToast('Horaires enregistrés', 'success');
        } else {
            showToast('Erreur lors de l\'enregistrement', 'error');
        }
    } catch (error) {
        showToast('Erreur: ' + error.message, 'error');
    }
}

// Charger les paramètres d'absence quand on accède aux paramètres
const originalShowSection = showSection;
showSection = function(section) {
    originalShowSection(section);
    if (section === 'settings') {
        loadAwaySettings();
    }
};
