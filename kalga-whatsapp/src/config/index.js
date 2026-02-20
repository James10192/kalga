/**
 * Configuration centralisée de l'application
 * Charge les variables d'environnement et exporte un objet de configuration typé
 */
require('dotenv').config();
const path = require('path');

const config = {
    // Application
    env: process.env.NODE_ENV || 'development',
    port: parseInt(process.env.PORT || '3001', 10),

    // KALGA API
    kalgaApiUrl: process.env.KALGA_API_URL || 'http://localhost:8001',
    apiTimeout: parseInt(process.env.API_TIMEOUT || '30000', 10),

    // Paths
    sessionsDir: path.join(process.cwd(), 'sessions'),
    uploadsDir: path.join(process.cwd(), '..', 'kalga-api', 'uploads'),
    logsDir: path.join(process.cwd(), 'logs'),

    // WhatsApp
    maxReconnectAttempts: parseInt(process.env.MAX_RECONNECT_ATTEMPTS || '5', 10),
    reconnectBaseDelay: parseInt(process.env.RECONNECT_BASE_DELAY || '5000', 10),
    maxReconnectDelay: parseInt(process.env.MAX_RECONNECT_DELAY || '30000', 10),

    // Anti-ban
    minTypingDelay: parseInt(process.env.MIN_TYPING_DELAY || '4000', 10),
    maxTypingDelay: parseInt(process.env.MAX_TYPING_DELAY || '7000', 10),
    initialDelay: parseInt(process.env.INITIAL_DELAY || '1000', 10),

    // Messages
    maxMessageLength: parseInt(process.env.MAX_MESSAGE_LENGTH || '2000', 10),

    // Logging
    logLevel: process.env.LOG_LEVEL || 'info',
    debug: process.env.DEBUG === 'true',
};

// Validation de la configuration
function validateConfig() {
    const required = ['port', 'kalgaApiUrl'];
    const missing = required.filter(key => !config[key]);

    if (missing.length > 0) {
        throw new Error(`Configuration manquante: ${missing.join(', ')}`);
    }

    return true;
}

module.exports = { config, validateConfig };
