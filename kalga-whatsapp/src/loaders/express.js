/**
 * Configuration Express
 */
const express = require('express');
const cors = require('cors');
const routes = require('../api/routes');

/**
 * Configure et retourne l'application Express
 */
function createExpressApp() {
    const app = express();

    // Middlewares
    app.use(express.json());
    app.use(cors());

    // Routes
    app.use('/', routes);

    return app;
}

module.exports = { createExpressApp };
