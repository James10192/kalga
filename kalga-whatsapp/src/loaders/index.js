/**
 * Orchestration du démarrage de l'application
 */
const { config, validateConfig } = require('../config');
const { logger, getLogFileName } = require('../utils/logger');
const { createExpressApp } = require('./express');
const { whatsappService } = require('../services/whatsapp.service');
const { messageService } = require('../services/message.service');

/**
 * Initialise l'application
 */
async function init() {
    logger.info('========================================');
    logger.info('KALGA WhatsApp Bridge DÉMARRAGE', {
        port: config.port,
        apiUrl: config.kalgaApiUrl,
        env: config.env,
    });
    logger.info('Fichier de log', { path: getLogFileName() });
    logger.info('========================================');

    // Valider la configuration
    validateConfig();

    // Configurer les handlers de messages
    whatsappService.onClientMessage = messageService.handleClientMessage.bind(messageService);
    whatsappService.onMerchantCommand = messageService.handleMerchantCommand.bind(messageService);

    // Créer l'application Express
    const app = createExpressApp();

    return app;
}

/**
 * Démarre le serveur
 */
function startServer(app) {
    app.listen(config.port, () => {
        logger.info('Serveur démarré', { port: config.port });
        console.log(`\n💡 Pour connecter un marchand:`);
        console.log(`   POST /connect { "merchant_phone": "22500000000" }`);
        console.log(`   Puis visiter /qr/22500000000 pour scanner le QR\n`);
    });
}

/**
 * Configure les gestionnaires d'arrêt
 */
function setupShutdownHandlers() {
    process.on('SIGINT', async () => {
        logger.info('Arrêt du bridge...');
        // Fermer proprement les connexions si nécessaire
        process.exit(0);
    });

    process.on('uncaughtException', (err) => {
        logger.error('Erreur non capturée', { error: err.message, stack: err.stack });
    });

    process.on('unhandledRejection', (reason, promise) => {
        logger.error('Promise rejetée', { reason: String(reason) });
    });
}

module.exports = {
    init,
    startServer,
    setupShutdownHandlers,
};
