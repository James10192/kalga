/**
 * Routes de connexion WhatsApp
 */
const express = require('express');
const qrcode = require('qrcode-terminal');
const { whatsappService } = require('../../services/whatsapp.service');
const { logger } = require('../../utils/logger');

const router = express.Router();

/**
 * POST /connect - Connecter un marchand
 */
router.post('/connect', async (req, res) => {
    const { merchant_phone } = req.body;

    if (!merchant_phone) {
        return res.status(400).json({ error: 'merchant_phone requis' });
    }

    try {
        await whatsappService.getOrCreateClient(merchant_phone);

        res.json({
            success: true,
            message: `Client WhatsApp initialisé pour ${merchant_phone}`,
            status: whatsappService.getClientStatus(merchant_phone),
        });
    } catch (error) {
        logger.error('Erreur connexion', { error: error.message });
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
            <head><title>KALGA - ${merchant_phone}</title></head>
            <body style="font-family: Arial; text-align: center; margin: 50px;">
                <h1 style="color: #25d366;">✅ Déjà connecté!</h1>
                <p>WhatsApp pour ${merchant_phone} est prêt.</p>
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
                <title>KALGA QR - ${merchant_phone}</title>
                <meta http-equiv="refresh" content="10">
                <style>
                    body { font-family: Arial; text-align: center; margin: 20px; }
                    .qr { font-family: monospace; font-size: 6px; line-height: 6px; white-space: pre; }
                </style>
            </head>
            <body>
                <h1 style="color: #25d366;">Scanner le QR Code</h1>
                <p>Marchand: ${merchant_phone}</p>
                <pre class="qr">${qrAscii}</pre>
                <p>Page auto-refresh toutes les 10s</p>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <html>
            <head>
                <title>KALGA - ${merchant_phone}</title>
                <meta http-equiv="refresh" content="5">
            </head>
            <body style="font-family: Arial; text-align: center; margin: 50px;">
                <h1>⏳ Chargement...</h1>
                <p>QR Code en cours de génération pour ${merchant_phone}</p>
            </body>
            </html>
        `);
    }
});

module.exports = router;
