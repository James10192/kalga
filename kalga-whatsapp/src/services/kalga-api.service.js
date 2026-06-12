/**
 * Client pour l'API KALGA
 * Gère toutes les communications avec le backend Python
 */
const axios = require('axios');
const { config } = require('../config');
const { logger } = require('../utils/logger');

class KalgaApiService {
    constructor() {
        this.client = axios.create({
            baseURL: config.kalgaApiUrl,
            timeout: config.apiTimeout,
            headers: {
                'Content-Type': 'application/json',
                // Verrou interne API <-> bridge : l'API rejette /incoming sans cette clé.
                ...(config.internalApiKey ? { 'X-Internal-Key': config.internalApiKey } : {}),
            },
        });
    }

    /**
     * Envoie un message client entrant à l'API
     * @param {object} params - Paramètres du message
     * @returns {Promise<object>} Réponse de l'API
     */
    async sendIncomingMessage({ merchantPhone, clientPhone, message, productCode, clientName }) {
        try {
            logger.info('Envoi à KALGA API', { merchantPhone, clientPhone, productCode });

            // Tronquer le message si trop long
            const truncatedMessage = message.length > config.maxMessageLength
                ? message.substring(0, config.maxMessageLength)
                : message;

            const response = await this.client.post('/api/chat/incoming', {
                merchant_phone: merchantPhone,
                client_phone: clientPhone,
                message: truncatedMessage,
                product_code: productCode,
                client_name: clientName || '',
            });

            return response.data;

        } catch (error) {
            logger.error('Erreur API chat/incoming', {
                error: error.message,
                status: error.response?.status,
            });
            throw error;
        }
    }

    /**
     * Envoie une commande marchand à l'API
     * @param {object} params - Paramètres de la commande
     * @returns {Promise<object>} Réponse de l'API
     */
    async sendMerchantCommand({ merchantPhone, message, imagePath }) {
        try {
            logger.info('Envoi commande marchand', { merchantPhone, hasImage: !!imagePath });

            const response = await this.client.post('/api/merchant/command', {
                merchant_phone: merchantPhone,
                message: message,
                image_path: imagePath,
            });

            logger.info('Réponse API commande', { action: response.data.action });
            return response.data;

        } catch (error) {
            logger.error('Erreur API merchant/command', {
                error: error.message,
                status: error.response?.status,
                data: error.response?.data,
            });
            throw error;
        }
    }

    /**
     * Envoie un média (note vocale ou image client) à l'API pour traitement
     * @param {object} params
     * @returns {Promise<object>} Réponse de l'API (même format que sendIncomingMessage)
     */
    async sendIncomingMedia({ merchantPhone, clientPhone, clientName, mediaPath, mediaType }) {
        try {
            logger.info('Envoi média à KALGA API', { merchantPhone, clientPhone, mediaType });

            const FormData = require('form-data');
            const fs = require('fs');
            const path = require('path');

            const form = new FormData();
            form.append('merchant_phone', merchantPhone);
            form.append('client_phone', clientPhone);
            form.append('client_name', clientName || '');
            form.append('media_type', mediaType);

            const mimeType = mediaType === 'audio' ? 'audio/ogg' : 'image/jpeg';
            form.append('file', fs.createReadStream(mediaPath), {
                filename: path.basename(mediaPath),
                contentType: mimeType,
            });

            const response = await this.client.post('/api/chat/incoming-media', form, {
                headers: {
                    ...form.getHeaders(),
                    // FormData remplace les headers par défaut : réinjecter le verrou interne.
                    ...(config.internalApiKey ? { 'X-Internal-Key': config.internalApiKey } : {}),
                },
                timeout: 60000, // 60s — transcription peut prendre du temps
            });

            return response.data;
        } catch (error) {
            logger.error('Erreur API chat/incoming-media', {
                error: error.message,
                status: error.response?.status,
            });
            throw error;
        }
    }

    /**
     * Vérifie la santé de l'API
     * @returns {Promise<boolean>}
     */
    async healthCheck() {
        try {
            const response = await this.client.get('/health', { timeout: 5000 });
            return response.status === 200;
        } catch (error) {
            return false;
        }
    }
}

// Instance singleton
const kalgaApiService = new KalgaApiService();

module.exports = { KalgaApiService, kalgaApiService };
