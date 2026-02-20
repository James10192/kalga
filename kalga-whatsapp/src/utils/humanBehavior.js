/**
 * Simulation de comportement humain pour éviter les bans WhatsApp
 * Ajoute des délais réalistes et des indicateurs de présence
 */
const { config } = require('../config');
const { logger } = require('./logger');

/**
 * Attend un délai aléatoire
 * @param {number} min - Délai minimum en ms
 * @param {number} max - Délai maximum en ms
 * @returns {Promise<void>}
 */
async function randomDelay(min, max) {
    const delay = min + Math.random() * (max - min);
    return new Promise(resolve => setTimeout(resolve, delay));
}

/**
 * Simule un comportement humain avant d'envoyer un message
 * @param {object} sock - Socket WhatsApp
 * @param {object} messageKey - Clé du message reçu
 * @param {string} jid - JID du destinataire
 * @param {string} merchantPhone - Numéro du marchand (optionnel)
 * @param {function} isClientReady - Fonction pour vérifier si le client est prêt
 */
async function simulateHumanBehavior(sock, messageKey, jid, merchantPhone = null, isClientReady = () => true) {
    try {
        logger.debug('Simulation comportement humain...', { jid });

        // 1. Marquer le message comme lu (ignorer les erreurs)
        try {
            await sock.readMessages([messageKey]);
            logger.debug('Message marqué comme lu');
        } catch (readErr) {
            // Ignorer silencieusement
        }

        // 2. Petit délai avant de commencer à "taper"
        await randomDelay(config.initialDelay, config.initialDelay * 2);

        // 3. Envoyer "en train d'écrire"
        try {
            if (!merchantPhone || isClientReady(merchantPhone)) {
                await sock.presenceSubscribe(jid);
                await sock.sendPresenceUpdate('composing', jid);
                logger.debug('Statut "en train d\'écrire" envoyé');
            }
        } catch (presErr) {
            // Ignorer silencieusement
        }

        // 4. Délai de frappe réaliste
        const typingDelay = config.minTypingDelay + Math.random() * (config.maxTypingDelay - config.minTypingDelay);
        logger.info(`Attente ${(typingDelay / 1000).toFixed(1)}s avant réponse...`);
        await new Promise(resolve => setTimeout(resolve, typingDelay));

        // 5. Arrêter le statut "en train d'écrire"
        try {
            if (!merchantPhone || isClientReady(merchantPhone)) {
                await sock.sendPresenceUpdate('paused', jid);
            }
        } catch (pauseErr) {
            // Ignorer silencieusement
        }

        logger.debug('Simulation terminée, envoi du message...');

    } catch (err) {
        logger.error('Erreur simulation humaine', { error: err.message });
        // Continuer même en cas d'erreur
    }
}

module.exports = {
    randomDelay,
    simulateHumanBehavior,
};
