/**
 * Service de gestion des médias
 * Téléchargement et sauvegarde des images WhatsApp
 */
const fs = require('fs');
const path = require('path');
const { downloadMediaMessage } = require('@whiskeysockets/baileys');
const { config } = require('../config');
const { logger } = require('../utils/logger');

class MediaService {
    constructor() {
        // Créer le dossier uploads s'il n'existe pas
        if (!fs.existsSync(config.uploadsDir)) {
            fs.mkdirSync(config.uploadsDir, { recursive: true });
            logger.info('Dossier uploads créé', { path: config.uploadsDir });
        }
    }

    /**
     * Télécharge et sauvegarde une image WhatsApp
     * @param {object} sock - Socket WhatsApp
     * @param {object} message - Message contenant l'image
     * @param {string} merchantPhone - Numéro du marchand
     * @returns {Promise<string|null>} Nom du fichier sauvegardé ou null
     */
    async downloadAndSaveImage(sock, message, merchantPhone) {
        try {
            const imageMessage = message.message?.imageMessage;
            if (!imageMessage) {
                logger.warn('Pas d\'image dans le message', {
                    keys: Object.keys(message.message || {}),
                });
                return null;
            }

            logger.info('Téléchargement de l\'image...', {
                mimetype: imageMessage.mimetype,
            });

            // Télécharger l'image
            const buffer = await downloadMediaMessage(message, 'buffer', {}, {
                logger: console,
                reuploadRequest: sock.updateMediaMessage,
            });

            if (!buffer || buffer.length === 0) {
                logger.error('Buffer vide après téléchargement');
                return null;
            }

            logger.info('Buffer reçu', { bytes: buffer.length });

            // Générer un nom unique pour l'image
            const timestamp = Date.now();
            const randomId = Math.random().toString(36).substring(2, 8);
            const ext = imageMessage.mimetype?.includes('png') ? 'png' : 'jpg';
            const filename = `${merchantPhone}_${timestamp}_${randomId}.${ext}`;
            const filepath = path.join(config.uploadsDir, filename);

            // Sauvegarder l'image
            fs.writeFileSync(filepath, buffer);
            logger.info('Image sauvegardée', { filename, bytes: buffer.length });

            // Vérifier que le fichier existe
            if (!fs.existsSync(filepath)) {
                logger.error('Fichier non créé!');
                return null;
            }

            return filename;

        } catch (error) {
            logger.error('Erreur téléchargement image', {
                error: error.message,
                stack: error.stack,
            });
            return null;
        }
    }

    /**
     * Lit une image pour l'envoyer
     * @param {string} filename - Nom du fichier
     * @returns {Buffer|null} Buffer de l'image ou null
     */
    readImage(filename) {
        try {
            const fullPath = path.join(config.uploadsDir, filename);
            if (!fs.existsSync(fullPath)) {
                logger.error('Image non trouvée', { path: fullPath });
                return null;
            }
            return fs.readFileSync(fullPath);
        } catch (error) {
            logger.error('Erreur lecture image', { error: error.message });
            return null;
        }
    }

    /**
     * Vérifie si un fichier image existe
     * @param {string} filename - Nom du fichier
     * @returns {boolean}
     */
    imageExists(filename) {
        const fullPath = path.join(config.uploadsDir, filename);
        return fs.existsSync(fullPath);
    }
}

// Instance singleton
const mediaService = new MediaService();

module.exports = { MediaService, mediaService };
