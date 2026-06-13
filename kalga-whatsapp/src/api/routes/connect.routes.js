/**
 * Routes de connexion WhatsApp
 */
const express = require('express');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const { whatsappService } = require('../../services/whatsapp.service');
const { logger } = require('../../utils/logger');

const router = express.Router();

/**
 * Valide qu'un numéro de téléphone ne contient que des chiffres (8-15 digits)
 */
function isValidPhone(phone) {
    return /^\d{8,15}$/.test(phone);
}

/**
 * Échappe le HTML pour éviter les XSS
 */
function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, (c) => map[c]);
}

/**
 * POST /connect - Connecter un marchand
 */
router.post('/connect', async (req, res) => {
    const { merchant_phone } = req.body;

    if (!merchant_phone || !isValidPhone(merchant_phone)) {
        return res.status(400).json({ error: 'merchant_phone requis (8-15 chiffres)' });
    }

    try {
        await whatsappService.getOrCreateClient(merchant_phone);

        res.json({
            success: true,
            message: `Client WhatsApp initialisé pour ${escapeHtml(merchant_phone)}`,
            status: whatsappService.getClientStatus(merchant_phone),
        });
    } catch (error) {
        logger.error('Erreur connexion', { error: error.message });
        res.status(500).json({ error: error.message });
    }
});

/**
 * GET /pairing-code/:merchant_phone - Code d'appairage WhatsApp (lien par numero)
 */
router.get('/pairing-code/:merchant_phone', async (req, res) => {
    const { merchant_phone } = req.params;

    if (!isValidPhone(merchant_phone)) {
        return res.status(400).json({ error: 'merchant_phone invalide (8-15 chiffres)' });
    }

    try {
        const pairingCode = await whatsappService.requestPairingCode(merchant_phone);

        if (pairingCode === null) {
            return res.status(409).json({ error: 'Deja connecte', linked: true });
        }

        if (pairingCode === 'pending') {
            return res.status(202).json({ pairingCode: null, pending: true });
        }

        res.json({ pairingCode });
    } catch (error) {
        if (error.message === 'rate_limited') {
            return res.status(429).json({
                error: 'Trop de tentatives, patientez quelques minutes avant de reessayer',
            });
        }
        logger.error('Erreur code appairage', { error: error.message });
        res.status(500).json({ error: error.message });
    }
});

/**
 * GET /qr/:merchant_phone - Page QR Code
 */
router.get('/qr/:merchant_phone', (req, res) => {
    const { merchant_phone } = req.params;
    const status = whatsappService.getClientStatus(merchant_phone);

    if (!status) {
        return res.status(404).json({
            error: 'Marchand non trouvé. Utilisez POST /connect d\'abord.',
        });
    }

    if (status.ready) {
        res.send(`
            <html>
            <head><title>KALGA - ${escapeHtml(merchant_phone)}</title></head>
            <body style="font-family: Arial; text-align: center; margin: 50px;">
                <h1 style="color: #25d366;">✅ Déjà connecté!</h1>
                <p>WhatsApp pour ${escapeHtml(merchant_phone)} est prêt.</p>
            </body>
            </html>
        `);
    } else if (status.qrCode) {
        // Générer QR en ASCII
        let qrAscii = '';
        const originalWrite = process.stdout.write.bind(process.stdout);
        process.stdout.write = (chunk) => { qrAscii += chunk; return true; };
        qrcode.generate(status.qrCode, { small: true });
        process.stdout.write = originalWrite;

        res.send(`
            <html>
            <head>
                <title>KALGA QR - ${escapeHtml(merchant_phone)}</title>
                <meta http-equiv="refresh" content="10">
                <style>
                    body { font-family: Arial; text-align: center; margin: 20px; }
                    .qr { font-family: monospace; font-size: 6px; line-height: 6px; white-space: pre; }
                </style>
            </head>
            <body>
                <h1 style="color: #25d366;">Scanner le QR Code</h1>
                <p>Marchand: ${escapeHtml(merchant_phone)}</p>
                <pre class="qr">${qrAscii}</pre>
                <p>Page auto-refresh toutes les 10s</p>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <html>
            <head>
                <title>KALGA - ${escapeHtml(merchant_phone)}</title>
                <meta http-equiv="refresh" content="5">
            </head>
            <body style="font-family: Arial; text-align: center; margin: 50px;">
                <h1>⏳ Chargement...</h1>
                <p>QR Code en cours de génération pour ${escapeHtml(merchant_phone)}</p>
            </body>
            </html>
        `);
    }
});

/**
 * GET /qr-image/:merchant_phone - QR Code en PNG (scannable)
 */
router.get('/qr-image/:merchant_phone', async (req, res) => {
    const { merchant_phone } = req.params;
    const status = whatsappService.getClientStatus(merchant_phone);

    if (!status || !status.qrCode) {
        return res.status(404).json({ error: 'QR Code non disponible' });
    }

    try {
        const png = await QRCode.toBuffer(status.qrCode, {
            width: 500,
            margin: 4,
            color: { dark: '#000000', light: '#ffffff' },
        });
        res.set('Content-Type', 'image/png');
        res.set('Cache-Control', 'no-store');
        res.send(png);
    } catch (err) {
        logger.error('Erreur génération QR PNG', { error: err.message });
        res.status(500).json({ error: err.message });
    }
});

module.exports = router;
