/**
 * Configuration Express
 */
const express = require('express');
const cors = require('cors');
const routes = require('../api/routes');
const { config } = require('../config');

/**
 * Middleware d'authentification par clé API interne.
 * Protège les routes POST (send, connect) tout en laissant GET ouvert (health, status, QR).
 */
function internalAuthMiddleware(req, res, next) {
    // GET requests are public (health check, QR page, status)
    if (req.method === 'GET') return next();

    // Skip auth if no key configured (dev mode warning printed at startup)
    if (!config.internalApiKey) return next();

    const provided = req.headers['x-internal-key'];
    if (provided !== config.internalApiKey) {
        return res.status(401).json({ error: 'Unauthorized — invalid or missing X-Internal-Key header' });
    }
    next();
}

/**
 * Configure et retourne l'application Express
 */
function createExpressApp() {
    const app = express();

    // Middlewares
    app.use(express.json());
    app.use(cors({
        origin: config.allowedOrigins,
        methods: ['GET', 'POST'],
    }));
    app.use(internalAuthMiddleware);

    // Routes
    app.use('/', routes);

    return app;
}

module.exports = { createExpressApp };
