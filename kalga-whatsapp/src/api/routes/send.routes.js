/**
 * Routes d'envoi de messages
 */
const express = require('express');
const { whatsappService } = require('../../services/whatsapp.service');
const { logger } = require('../../utils/logger');

const router = express.Router();

/**
 * POST /send - Envoyer un message texte
 */
router.post('/send', async (req, res) => {
    const { merchant_phone, to, message } = req.body;

    if (!merchant_phone || !to || !message) {
        return res.status(400).json({ error: 'merchant_phone, to et message requis' });
    }

    if (!whatsappService.isClientReady(merchant_phone)) {
        return res.status(503).json({ error: 'Client WhatsApp non prêt' });
    }

    try {
        const sent = await whatsappService.sendMessage(merchant_phone, to, message);
        if (sent) {
            res.json({ success: true, to, message: message.substring(0, 50) + '...' });
        } else {
            res.status(500).json({ error: 'Failed to send message' });
        }
    } catch (error) {
        logger.error('Erreur envoi message', { error: error.message });
        res.status(500).json({ error: error.message });
    }
});

/**
 * POST /send-image - Envoyer une image
 */
router.post('/send-image', async (req, res) => {
    const { merchant_phone, to, image_path, caption } = req.body;

    if (!merchant_phone || !to || !image_path) {
        return res.status(400).json({ error: 'merchant_phone, to et image_path requis' });
    }

    if (!whatsappService.isClientReady(merchant_phone)) {
        return res.status(503).json({ error: 'Client WhatsApp non prêt' });
    }

    try {
        const sent = await whatsappService.sendImage(merchant_phone, to, image_path, caption || '');
        if (sent) {
            res.json({ success: true, to, image_path });
        } else {
            res.status(500).json({ error: 'Failed to send image' });
        }
    } catch (error) {
        logger.error('Erreur envoi image', { error: error.message });
        res.status(500).json({ error: error.message });
    }
});

/**
 * POST /send-location - Envoyer une localisation GPS
 */
router.post('/send-location', async (req, res) => {
    const { merchant_phone, to, latitude, longitude, name, address } = req.body;

    if (!merchant_phone || !to || latitude === undefined || longitude === undefined) {
        return res.status(400).json({ error: 'merchant_phone, to, latitude et longitude requis' });
    }

    if (!whatsappService.isClientReady(merchant_phone)) {
        return res.status(503).json({ error: 'Client WhatsApp non prêt' });
    }

    try {
        const sent = await whatsappService.sendLocation(merchant_phone, to, {
            latitude,
            longitude,
            name,
            address,
        });
        if (sent) {
            res.json({ success: true, to, latitude, longitude });
        } else {
            res.status(500).json({ error: 'Failed to send location' });
        }
    } catch (error) {
        logger.error('Erreur envoi localisation', { error: error.message });
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
