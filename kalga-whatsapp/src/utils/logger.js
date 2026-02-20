/**
 * Système de logging structuré
 * Écrit dans la console et dans des fichiers de log quotidiens
 */
const fs = require('fs');
const path = require('path');
const { config } = require('../config');

// Créer le dossier de logs s'il n'existe pas
if (!fs.existsSync(config.logsDir)) {
    fs.mkdirSync(config.logsDir, { recursive: true });
}

/**
 * Obtient le nom du fichier de log du jour
 */
function getLogFileName() {
    const now = new Date();
    const date = now.toISOString().split('T')[0]; // YYYY-MM-DD
    return path.join(config.logsDir, `whatsapp-${date}.log`);
}

/**
 * Écrit une entrée de log
 */
function log(level, message, data = null) {
    const now = new Date();
    const timestamp = now.toISOString();
    let logLine = `[${timestamp}] [${level}] ${message}`;

    if (data) {
        logLine += ` | ${JSON.stringify(data)}`;
    }

    // Afficher dans la console
    console.log(logLine);

    // Écrire dans le fichier
    try {
        fs.appendFileSync(getLogFileName(), logLine + '\n');
    } catch (err) {
        console.error('Erreur écriture log:', err.message);
    }
}

// API de logging
const logger = {
    info: (msg, data) => log('INFO', msg, data),
    warn: (msg, data) => log('WARN', msg, data),
    error: (msg, data) => log('ERROR', msg, data),
    debug: (msg, data) => {
        if (config.debug || config.logLevel === 'debug') {
            log('DEBUG', msg, data);
        }
    },
    message: (msg, data) => log('MSG', msg, data),
};

module.exports = { logger, getLogFileName };
