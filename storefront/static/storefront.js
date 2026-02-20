/**
 * KALGA Storefront v3 - Premium E-commerce
 * Inspired by Cataleyas / Bouquet de Fruits / prAna
 */

const API_BASE = window.location.origin;

// ========== SVG ICONS ==========

const ICONS = {
    camera: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 15.2a3.2 3.2 0 100-6.4 3.2 3.2 0 000 6.4z"/><path d="M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z"/></svg>',
    pin: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 010-5 2.5 2.5 0 010 5z"/></svg>',
    whatsapp: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>',
    order: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
    arrowLeft: '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>',
    arrowDown: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>',
    chevronLeft: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>',
    chevronRight: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>',
    alert: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
    package: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2c0 1.66 1.34 3 3 3s3-1.34 3-3h6c0 1.66 1.34 3 3 3s3-1.34 3-3h2v-5l-3-4zM6 18.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm13.5-9l1.96 2.5H17V9.5h2.5zm-1.5 9c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>',
    phone: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>',
};

// ========== UTILITIES ==========

function formatPrice(price) {
    return new Intl.NumberFormat('fr-FR').format(Math.round(price));
}

function getParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

function formatPhoneForWhatsApp(phone) {
    if (phone && phone.startsWith('225') && phone.length === 12) {
        return '225' + '0' + phone.substring(3);
    }
    return phone;
}

function getInitials(name) {
    if (!name) return '?';
    return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function handleImageError(img) {
    const placeholder = document.createElement('div');
    placeholder.className = 'card-image-placeholder';
    placeholder.innerHTML = ICONS.camera;
    img.parentNode.replaceChild(placeholder, img);
}

function showLoading(container) {
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Chargement...</p></div>';
}

function showError(container, message) {
    container.innerHTML = `
        <div class="error-state">
            ${ICONS.alert}
            <p>${message}</p>
            <button class="btn btn-back mt-16" onclick="history.back()">
                ${ICONS.arrowLeft} Retour
            </button>
        </div>
    `;
}

function showEmpty(container, message) {
    container.innerHTML = `<div class="empty-state">${ICONS.package}<p>${message}</p></div>`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== NAV BAR (shared across all pages) ==========

function renderNav(merchant, options = {}) {
    const nav = document.getElementById('site-nav');
    if (!nav) return;

    const storeName = merchant.business_name || merchant.name || '';
    const initials = getInitials(storeName);
    const waPhone = formatPhoneForWhatsApp(merchant.phone);
    const boutiqueUrl = `boutique.html?m=${merchant.phone}`;

    const logoHTML = merchant.logo_url
        ? `<img class="nav-logo" src="${API_BASE}${merchant.logo_url}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><span class="nav-logo-initials" style="display:none">${escapeHtml(initials)}</span>`
        : `<span class="nav-logo-initials">${escapeHtml(initials)}</span>`;

    const aboutLink = merchant.about
        ? `<a href="${boutiqueUrl}#about" class="nav-link">A propos</a>`
        : '';

    nav.innerHTML = `
        <a href="${boutiqueUrl}" class="nav-brand">
            ${logoHTML}
            <span class="nav-store-name">${escapeHtml(storeName)}</span>
        </a>
        <div class="nav-links">
            ${aboutLink}
            <a href="https://wa.me/${waPhone}" target="_blank" class="nav-link nav-link-wa">
                ${ICONS.whatsapp}
            </a>
        </div>
    `;

    // Scroll shadow effect
    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 10);
    }, { passive: true });
}

// ========== SCROLL REVEAL ==========

function initScrollReveal() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

// ========== API ==========

async function apiGet(endpoint) {
    const r = await fetch(`${API_BASE}${endpoint}`);
    if (!r.ok) throw new Error(`Erreur ${r.status}`);
    return r.json();
}

async function apiPost(endpoint, data) {
    const r = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return r.json();
}

// ========== BOUTIQUE PAGE ==========

async function loadBoutique() {
    const phone = getParam('m');
    const gridEl = document.getElementById('product-grid');

    if (!phone) {
        showError(gridEl, 'Aucun marchand specifie.');
        return;
    }

    try {
        const data = await apiGet(`/api/storefront/${phone}/products`);
        const merchant = data.merchant;
        const products = data.products;

        document.title = `${merchant.business_name || merchant.name} - Boutique`;

        // Render navigation
        renderNav(merchant);

        // Render hero
        renderHero(merchant, products.length);

        // Group variants
        const grouped = [];
        const seenGroups = new Set();

        for (const p of products) {
            if (p.group_id) {
                if (seenGroups.has(p.group_id)) continue;
                seenGroups.add(p.group_id);
                const groupProducts = products.filter(x => x.group_id === p.group_id);
                const main = groupProducts.find(x => !x.variant_name) || groupProducts[0];
                grouped.push({ ...main, _variantCount: groupProducts.length });
            } else {
                grouped.push({ ...p, _variantCount: 0 });
            }
        }

        // Section header
        const sectionHeader = document.getElementById('section-header');
        if (sectionHeader) {
            sectionHeader.innerHTML = `
                <span class="section-title">Collection</span>
                <span class="section-count">${grouped.length} produit${grouped.length > 1 ? 's' : ''}</span>
            `;
        }

        if (grouped.length === 0) {
            showEmpty(gridEl, 'Aucun produit disponible pour le moment.');
            return;
        }

        // Render cards
        gridEl.innerHTML = grouped.map(p => {
            const imgHTML = p.image_url
                ? `<img class="card-image" src="${API_BASE}${p.image_url}" alt="${escapeHtml(p.name)}" loading="lazy" onerror="handleImageError(this)">`
                : `<div class="card-image-placeholder">${ICONS.camera}</div>`;

            const badgesHTML = `
                <div class="card-badges">
                    ${p._variantCount > 1 ? `<span class="badge badge-variants">${p._variantCount} variantes</span>` : ''}
                    <span class="badge ${p.in_stock ? 'badge-in-stock' : 'badge-out-of-stock'}">${p.in_stock ? 'En stock' : 'Rupture'}</span>
                </div>
            `;

            return `
                <a href="produit.html?code=${p.code.replace('#', '')}" class="product-card reveal">
                    <div class="card-image-wrap">
                        ${imgHTML}
                        ${badgesHTML}
                    </div>
                    <div class="card-body">
                        <div class="card-name">${escapeHtml(p.name)}</div>
                        <div class="card-code">${p.code}</div>
                        <div class="card-price">${formatPrice(p.price)} <span class="currency">FCFA</span></div>
                    </div>
                </a>
            `;
        }).join('');

        // Render about section
        renderAbout(merchant);

        // Init animations
        initScrollReveal();

    } catch (error) {
        console.error('Erreur chargement boutique:', error);
        showError(gridEl, 'Impossible de charger la boutique. Verifiez le lien.');
    }
}

function renderHero(merchant, productCount) {
    const hero = document.getElementById('store-hero');
    if (!hero) return;

    const storeName = merchant.business_name || merchant.name || '';
    const initials = getInitials(storeName);

    // Banner image as background
    if (merchant.banner_url) {
        hero.classList.add('has-banner');
        hero.style.backgroundImage = `url(${API_BASE}${merchant.banner_url})`;
    }

    const logoHTML = merchant.logo_url
        ? `<img class="hero-logo" src="${API_BASE}${merchant.logo_url}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="hero-logo-initials" style="display:none">${escapeHtml(initials)}</div>`
        : `<div class="hero-logo-initials">${escapeHtml(initials)}</div>`;

    const taglineHTML = merchant.tagline
        ? `<p class="hero-tagline">${escapeHtml(merchant.tagline)}</p>`
        : '';

    const addressHTML = merchant.address
        ? `<div class="hero-address">${ICONS.pin} ${escapeHtml(merchant.address)}</div>`
        : '';

    hero.innerHTML = `
        <div class="hero-content">
            ${logoHTML}
            <h1 class="hero-store-name">${escapeHtml(storeName)}</h1>
            ${taglineHTML}
            ${addressHTML}
            <div class="hero-stat">
                <strong>${productCount}</strong> produit${productCount > 1 ? 's' : ''} disponible${productCount > 1 ? 's' : ''}
            </div>
            <br>
            <a href="#collection" class="hero-scroll-btn">
                Decouvrir ${ICONS.arrowDown}
            </a>
        </div>
    `;
}

function renderAbout(merchant) {
    const aboutEl = document.getElementById('about-section');
    if (!aboutEl || !merchant.about) {
        if (aboutEl) aboutEl.style.display = 'none';
        return;
    }

    const waPhone = formatPhoneForWhatsApp(merchant.phone);

    aboutEl.innerHTML = `
        <div class="about-divider">
            <span class="about-divider-label">A propos</span>
        </div>
        <p class="about-text">${escapeHtml(merchant.about)}</p>
        <div class="about-contact">
            ${merchant.address ? `<span class="about-contact-item">${ICONS.pin} ${escapeHtml(merchant.address)}</span>` : ''}
            <a href="https://wa.me/${waPhone}" target="_blank" class="about-contact-item">${ICONS.whatsapp} WhatsApp</a>
        </div>
    `;
    aboutEl.style.display = 'block';
}

// ========== PRODUCT DETAIL ==========

const gallery = {
    images: [],
    currentIndex: 0,

    init(product, variants) {
        this.images = [];

        if (product.image_url) {
            this.images.push({ url: product.image_url, variant_name: product.variant_name || '', code: product.code, price: product.price });
        }

        for (const v of variants) {
            if (v.image_url) {
                this.images.push({ url: v.image_url, variant_name: v.variant_name || '', code: v.code, price: v.price });
            }
        }

        if (this.images.length === 0) {
            this.images.push({ url: null, variant_name: '', code: product.code, price: product.price });
        }

        this.currentIndex = 0;
        this.render();
        this._initSwipe();
    },

    next() {
        if (this.images.length <= 1) return;
        this.currentIndex = (this.currentIndex + 1) % this.images.length;
        this.render();
    },

    prev() {
        if (this.images.length <= 1) return;
        this.currentIndex = (this.currentIndex - 1 + this.images.length) % this.images.length;
        this.render();
    },

    goTo(idx) {
        this.currentIndex = idx;
        this.render();
    },

    render() {
        const mainEl = document.getElementById('gallery-main-img');
        const thumbsEl = document.getElementById('gallery-thumbs');
        const dotsEl = document.getElementById('gallery-dots');
        const counterEl = document.getElementById('gallery-counter');
        const navBtns = document.querySelectorAll('.gallery-nav-btn');
        const current = this.images[this.currentIndex];

        // Main image
        if (current.url) {
            mainEl.innerHTML = `<img src="${API_BASE}${current.url}" alt="Produit" onerror="handleImageError(this)">`;
        } else {
            mainEl.innerHTML = `<div class="gallery-placeholder">${ICONS.camera}</div>`;
        }

        // Nav buttons
        navBtns.forEach(btn => btn.style.display = this.images.length > 1 ? 'flex' : 'none');

        // Counter
        if (counterEl) {
            counterEl.style.display = this.images.length > 1 ? 'block' : 'none';
            counterEl.textContent = `${this.currentIndex + 1} / ${this.images.length}`;
        }

        // Dots
        if (dotsEl && this.images.length > 1) {
            dotsEl.innerHTML = this.images.map((_, i) =>
                `<button class="gallery-dot ${i === this.currentIndex ? 'active' : ''}" onclick="gallery.goTo(${i})"></button>`
            ).join('');
            dotsEl.style.display = 'flex';
        } else if (dotsEl) {
            dotsEl.style.display = 'none';
        }

        // Thumbnails
        if (this.images.length > 1 && thumbsEl) {
            thumbsEl.innerHTML = this.images.map((img, i) => {
                if (!img.url) return '';
                return `<img class="gallery-thumb ${i === this.currentIndex ? 'active' : ''}" src="${API_BASE}${img.url}" alt="${escapeHtml(img.variant_name)}" onclick="gallery.goTo(${i})" onerror="this.style.display='none'">`;
            }).join('');
            thumbsEl.style.display = 'flex';
        } else if (thumbsEl) {
            thumbsEl.style.display = 'none';
        }

        // Variant info
        const variantEl = document.getElementById('product-variant');
        if (variantEl && current.variant_name) {
            variantEl.textContent = current.variant_name;
            variantEl.style.display = 'inline-block';
        } else if (variantEl) {
            variantEl.style.display = 'none';
        }

        // Active variant chip
        document.querySelectorAll('.variant-chip').forEach((chip, i) => {
            chip.classList.toggle('active', i === this.currentIndex);
        });
    },

    _initSwipe() {
        const el = document.getElementById('gallery-main-img');
        if (!el) return;
        let startX = 0, distX = 0;

        el.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, { passive: true });
        el.addEventListener('touchmove', e => { distX = e.touches[0].clientX - startX; }, { passive: true });
        el.addEventListener('touchend', () => {
            if (Math.abs(distX) > 50) { distX > 0 ? this.prev() : this.next(); }
            distX = 0;
        }, { passive: true });
    }
};

async function loadProductDetail() {
    const code = getParam('code');
    const container = document.getElementById('product-detail');

    if (!code) { showError(container, 'Aucun produit specifie.'); return; }

    showLoading(container);

    try {
        const data = await apiGet(`/api/storefront/product/${encodeURIComponent('#' + code)}`);
        const product = data.product;
        const variants = data.variants;
        const merchant = data.merchant;

        document.title = `${product.name} - ${merchant.business_name || merchant.name}`;

        // Render nav
        renderNav(merchant);

        const waText = encodeURIComponent(`Bonjour, je suis interesse(e) par ${product.name} ${product.code}`);
        const waLink = `https://wa.me/${formatPhoneForWhatsApp(merchant.phone)}?text=${waText}`;

        // Stock badge
        const stockBadge = product.in_stock
            ? '<div class="stock-badge stock-in"><span class="dot"></span> En stock</div>'
            : '<div class="stock-badge stock-out"><span class="dot"></span> Rupture de stock</div>';

        // Variant chips
        let variantChipsHTML = '';
        if (variants.length > 0) {
            const allItems = [product, ...variants];
            variantChipsHTML = `
                <div class="variant-chips">
                    ${allItems.map((v, i) => `<button class="variant-chip ${i === 0 ? 'active' : ''}" onclick="gallery.goTo(${i})">${escapeHtml(v.variant_name || v.name)}</button>`).join('')}
                </div>
            `;
        }

        container.innerHTML = `
            <a href="boutique.html?m=${merchant.phone}" class="btn btn-back" style="margin-bottom:16px">
                ${ICONS.arrowLeft} Retour a la boutique
            </a>

            <div class="product-detail-layout">
                <div class="gallery-section">
                    <div class="gallery-main" id="gallery-main-img">
                        <div class="gallery-placeholder">${ICONS.camera}</div>
                    </div>
                    <button class="gallery-nav-btn prev" onclick="gallery.prev()">${ICONS.chevronLeft}</button>
                    <button class="gallery-nav-btn next" onclick="gallery.next()">${ICONS.chevronRight}</button>
                    <span class="gallery-counter" id="gallery-counter"></span>
                    <div class="gallery-dots" id="gallery-dots"></div>
                    <div class="gallery-thumbnails" id="gallery-thumbs"></div>
                </div>

                <div class="product-info">
                    <h1>${escapeHtml(product.name)}</h1>
                    <div class="product-code">${product.code}</div>
                    <div class="product-price">${formatPrice(product.price)} <span class="currency">FCFA</span></div>
                    <div class="product-variant" id="product-variant" style="display:none"></div>
                    ${variantChipsHTML}
                    ${product.description ? `<p class="product-description">${escapeHtml(product.description)}</p>` : ''}
                    ${stockBadge}

                    <div class="action-buttons">
                        <a href="${waLink}" target="_blank" class="btn btn-whatsapp">
                            ${ICONS.whatsapp} Contacter sur WhatsApp
                        </a>
                        <a href="commander.html?code=${code}" class="btn btn-order">
                            ${ICONS.order} Commander
                        </a>
                    </div>
                </div>
            </div>
        `;

        gallery.init(product, variants);

    } catch (error) {
        console.error('Erreur chargement produit:', error);
        showError(container, 'Impossible de charger ce produit.');
    }
}

// ========== ORDER FORM ==========

async function loadOrderForm() {
    const code = getParam('code');
    const recapEl = document.getElementById('order-product-recap');
    const formEl = document.getElementById('order-form');

    if (!code) { showError(recapEl, 'Aucun produit specifie.'); return; }

    try {
        const data = await apiGet(`/api/storefront/product/${encodeURIComponent('#' + code)}`);
        const product = data.product;
        const merchant = data.merchant;

        // Render nav
        renderNav(merchant);

        formEl.dataset.merchantPhone = merchant.phone;
        formEl.dataset.productCode = product.code;

        recapEl.innerHTML = `
            <div class="order-product-recap">
                ${product.image_url ? `<img src="${API_BASE}${product.image_url}" alt="${escapeHtml(product.name)}" onerror="this.style.display='none'">` : ''}
                <div class="recap-info">
                    <div class="recap-name">${escapeHtml(product.name)}</div>
                    <div class="recap-price">${formatPrice(product.price)} FCFA</div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur chargement produit:', error);
        showError(recapEl, 'Impossible de charger les infos du produit.');
    }
}

async function submitOrder(event) {
    event.preventDefault();

    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const resultEl = document.getElementById('order-result');

    const merchantPhone = form.dataset.merchantPhone;
    const productCode = form.dataset.productCode;
    const clientName = form.querySelector('#client-name').value.trim();
    const countryCode = form.querySelector('#country-code').value;
    const clientPhone = countryCode + form.querySelector('#client-phone').value.trim();
    const message = form.querySelector('#client-message').value.trim();

    if (!clientName || !form.querySelector('#client-phone').value.trim()) {
        alert('Veuillez remplir votre nom et numero de telephone.');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Envoi en cours...';

    try {
        const result = await apiPost('/api/storefront/order', {
            merchant_phone: merchantPhone,
            product_code: productCode,
            client_name: clientName,
            client_phone: clientPhone,
            message: message || null
        });

        if (result.success) {
            form.style.display = 'none';
            resultEl.innerHTML = `
                <div class="success-message">
                    <div class="success-icon">${ICONS.check}</div>
                    <h3>Commande envoyee !</h3>
                    <p>Le marchand a ete notifie et vous contactera bientot sur votre WhatsApp.</p>
                    <a href="https://wa.me/${formatPhoneForWhatsApp(merchantPhone)}?text=${encodeURIComponent('Bonjour, je viens de passer une commande sur votre boutique.')}" target="_blank" class="btn btn-whatsapp mt-16">
                        ${ICONS.whatsapp} Contacter directement
                    </a>
                </div>
            `;
        } else {
            alert(result.message || 'Une erreur est survenue.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Envoyer la commande';
        }
    } catch (error) {
        console.error('Erreur soumission commande:', error);
        alert('Erreur de connexion. Veuillez reessayer.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Envoyer la commande';
    }
}
