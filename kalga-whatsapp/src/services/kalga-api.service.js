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
            headers: { 'Content-Type': 'application/json' },
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
