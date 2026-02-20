/**
 * Point d'entrée de l'application KALGA WhatsApp Bridge
 *
 * Architecture modulaire:
 * - config/     : Configuration centralisée
 * - api/        : Routes Express
 * - services/   : Logique métier
 * - utils/      : Utilitaires partagés
 * - loaders/    : Initialisation
 */
const { init, startServer, setupShutdownHandlers } = require('./loaders');

async function main() {
    // Configurer les gestionnaires d'arrêt
    setupShutdownHandlers();

    // Initialiser l'application
    const app = await init();

    // Démarrer le serveur
    startServer(app);
}

// Lancer l'application
main().catch((error) => {
    console.error('Erreur fatale au démarrage:', error);
    process.exit(1);
});
