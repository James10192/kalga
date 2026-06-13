/**
 * Routes de statut et santé
 */
const express = require('express');
const { config } = require('../../config');
const { whatsappService } = require('../../services/whatsapp.service');
const { getLogFileName } = require('../../utils/logger');

const router = express.Router();

/**
 * GET / - Page d'accueil
 */
router.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>KALGA WhatsApp Bridge</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
                h1 { color: #25d366; }
                .links { margin: 30px 0; }
                .links a {
                    display: inline-block;
                    margin: 10px;
                    padding: 10px 20px;
                    background: #25d366;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>KALGA WhatsApp Bridge (Baileys)</h1>
            <p>Service de connexion WhatsApp pour marchands</p>
            <div class="links">
                <a href="/status">Statut</a>
                <a href="/health">Health Check</a>
            </div>
            <p>Port: ${config.port}</p>
            <p>Environment: ${config.env}</p>
        </body>
        </html>
    `);
});

/**
 * GET /health - Health check
 */
router.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        uptime: process.uptime(),
        timestamp: new Date().toISOString(),
        environment: config.env,
    });
});

/**
 * GET /status - Statut global
 */
router.get('/status', (req, res) => {
    const statuses = whatsappService.getAllStatuses();
    const connectedCount = Object.values(statuses).filter(s => s.connected).length;

    res.json({
        service: 'kalga-whatsapp-bridge',
        version: '2.0.0',
        environment: config.env,
        merchants_connected: connectedCount,
        uptime: process.uptime(),
        log_file: getLogFileName(),
        statuses,
    });
});

/**
 * GET /status/:merchant_phone - Statut d'un marchand
 */
router.get('/status/:merchant_phone', (req, res) => {
    const { merchant_phone } = req.params;
    const status = whatsappService.getClientStatus(merchant_phone);

    // Pas encore de socket pour ce marchand = etat transitoire NORMAL pendant
    // l'onboarding : POST /connect cree la socket de facon asynchrone, donc le
    // poll frontend peut interroger /status avant qu'elle existe. On renvoie 200
    // avec un statut "non connecte" (et non un 404) pour que le polling continue
    // proprement, sans spammer la console d'erreurs.
    if (!status) {
        return res.json({
            merchant_phone,
            connected: false,
            ready: false,
            qrCode: null,
            pairingCode: null,
            realPhone: null,
        });
    }

    res.json({
        merchant_phone,
        ...status,
    });
});

module.exports = router;
