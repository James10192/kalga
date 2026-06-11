/**
 * Service de traitement des messages
 * Orchestre le traitement des messages clients et commandes marchands
 */
const { logger } = require('../utils/logger');
const { extractPhone, isGroupJid, isStatusBroadcast } = require('../utils/jid');
const { simulateHumanBehavior } = require('../utils/humanBehavior');
const { MessageBuffer } = require('../utils/messageBuffer');
const { config } = require('../config');
const { kalgaApiService } = require('./kalga-api.service');
const { mediaService } = require('./media.service');
const { whatsappService } = require('./whatsapp.service');

class MessageService {
    constructor() {
        // Rafales : les clients écrivent souvent en 2-3 messages rapprochés.
        // On les fusionne et on répond UNE fois (sérialisé par conversation).
        this.clientTextBuffer = new MessageBuffer({
            windowMs: config.messageBufferMs,
            onFlush: (key, items) => this._processClientBatch(key, items),
            onError: (error, key) => logger.error('Erreur traitement rafale',
                { key, error: error.message }),
        });
        // Préfixes de réponses du bot à ignorer
        this.botPrefixes = ['📦', '✅', '📋', '🛒', '🏷️', '💰', '💵', '👉', '❌', '⚠️', '⏳', '🔧', '📸'];

        // Mots-clés de réponses du bot à ignorer
        this.botKeywords = [
            'Création d\'un nouveau produit',
            'Quel est le *nom*',
            'Quel est le *prix*',
            'Étape',
            'produit créé',
            'Description enregistrée',
            'Image enregistrée',
            'Envoie une *photo*',
            'Commandes disponibles',
            'Tu veux la livraison',
            'passe au magasin',
        ];
    }

    /**
     * Traite un message client entrant
     */
    async handleClientMessage(merchantPhone, sock, message) {
        const senderJid = message.key.remoteJid;
        const senderPhoneRaw = extractPhone(senderJid);
        // Résoudre le LID vers le vrai numéro de téléphone si disponible
        const senderPhone = whatsappService.resolvePhone(senderPhoneRaw);
        const messageText = this._extractMessageText(message);

        // Traiter les notes vocales via transcription
        if (message.message?.audioMessage) {
            const isPtt = message.message.audioMessage.ptt === true;
            if (!isPtt) return; // Ignorer l'audio non-PTT (musique, etc.)

            // Vider la rafale texte en attente AVANT le média (ordre préservé)
            await this.clientTextBuffer.flushNow(`${merchantPhone}|${senderPhone}`);

            const voiceData = await mediaService.downloadVoiceNote(sock, message);
            if (!voiceData) {
                await whatsappService.sendMessage(
                    merchantPhone,
                    senderJid,
                    "Je n'ai pas pu écouter ton vocal, écris-moi stp 🙏"
                );
                return;
            }

            try {
                const response = await kalgaApiService.sendIncomingMedia({
                    merchantPhone,
                    clientPhone: senderPhone,
                    clientName: message.pushName || '',
                    mediaPath: voiceData.filepath,
                    mediaType: 'audio',
                });

                // Nettoyer le fichier temporaire après envoi
                try { require('fs').unlinkSync(voiceData.filepath); } catch (_) {}

                if (response && !response.no_response) {
                    const presenceType = response.audio_base64 ? 'recording' : 'composing';
                    await simulateHumanBehavior(
                        sock,
                        message.key,
                        senderJid,
                        merchantPhone,
                        () => whatsappService.isClientReady(merchantPhone),
                        presenceType
                    );
                    await this._sendBotResponse(merchantPhone, sock, senderJid, message, response);
                }
            } catch (error) {
                logger.error('Erreur traitement vocal', { error: error.message });
                try { require('fs').unlinkSync(voiceData.filepath); } catch (_) {}
            }
            return;
        }

        // Traiter les images client sans légende (recherche visuelle de produit)
        if (message.message?.imageMessage && !messageText) {
            await this.clientTextBuffer.flushNow(`${merchantPhone}|${senderPhone}`);
            const imageName = await mediaService.downloadAndSaveImage(sock, message, senderPhone);
            if (imageName) {
                const fullPath = require('path').join(require('../config').config.uploadsDir, imageName);
                try {
                    const response = await kalgaApiService.sendIncomingMedia({
                        merchantPhone,
                        clientPhone: senderPhone,
                        clientName: message.pushName || '',
                        mediaPath: fullPath,
                        mediaType: 'image',
                    });

                    // Nettoyer l'image de recherche client après envoi
                    try { require('fs').unlinkSync(fullPath); } catch (_) {}

                    if (response && !response.no_response) {
                        const presenceType = response.audio_base64 ? 'recording' : 'composing';
                        await simulateHumanBehavior(
                            sock,
                            message.key,
                            senderJid,
                            merchantPhone,
                            () => whatsappService.isClientReady(merchantPhone),
                            presenceType
                        );
                        await this._sendBotResponse(merchantPhone, sock, senderJid, message, response);
                    }
                } catch (error) {
                    logger.error('Erreur recherche visuelle', { error: error.message });
                    try { require('fs').unlinkSync(fullPath); } catch (_) {}
                }
            }
            return;
        }

        // Ignorer les messages vides
        if (!messageText) {
            logger.debug('Message sans texte ignoré');
            return;
        }

        // Ignorer si le client est le marchand lui-même
        if (senderPhone === merchantPhone) {
            logger.debug('Message du marchand à lui-même ignoré');
            return;
        }

        // Rafale : agréger les messages rapprochés du client et répondre UNE
        // seule fois, de façon cohérente (le traitement part de _processClientBatch).
        this.clientTextBuffer.push(`${merchantPhone}|${senderPhone}`, {
            sock,
            message,
            messageText,
            senderJid,
            senderPhone,
        });
    }

    /**
     * Traite un LOT de messages client (rafale fusionnée, sérialisé par client).
     * Le moteur multi-intentions de l'API reçoit la rafale entière en un appel
     * et répond une seule fois — plus de réponses croisées.
     */
    async _processClientBatch(key, items) {
        const merchantPhone = key.split('|')[0];
        const last = items[items.length - 1];
        const { sock, senderJid, senderPhone } = last;

        const combinedText = items.map(i => i.messageText).join('\n');
        const productCode = items
            .map(i => this._extractProductCode(i.message, i.messageText))
            .find(Boolean) || null;

        if (items.length > 1) {
            logger.info('Rafale fusionnée en un seul message', {
                count: items.length, clientPhone: senderPhone,
            });
        }
        logger.message('MESSAGE CLIENT', {
            merchantPhone,
            clientPhone: senderPhone,
            text: combinedText,
            productCode,
        });

        try {
            const response = await kalgaApiService.sendIncomingMessage({
                merchantPhone,
                clientPhone: senderPhone,
                message: combinedText,
                productCode,
                clientName: last.message.pushName || '',
            });

            if (response.no_response) {
                logger.warn('PAS DE RÉPONSE - conversation terminée', { senderPhone });
                return;
            }

            const presenceType = response.audio_base64 ? 'recording' : 'composing';
            await simulateHumanBehavior(
                sock,
                last.message.key,
                senderJid,
                merchantPhone,
                () => whatsappService.isClientReady(merchantPhone),
                presenceType
            );

            await this._sendBotResponse(merchantPhone, sock, senderJid, last.message, response);

        } catch (error) {
            logger.error('Erreur traitement message client', { error: error.message });
        }
    }

    /**
     * Envoie la réponse du bot (texte ou vocal PTT + images + localisation + goodbye)
     * Utilisé par les flux texte, vocal et visuel
     */
    async _sendBotResponse(merchantPhone, sock, senderJid, message, response) {
        const botResponse = response.message;
        if (!botResponse || botResponse.trim() === '') {
            logger.warn('MESSAGE VIDE reçu de l\'API', { senderJid });
            return;
        }

        let sent = false;
        if (response.audio_base64) {
            // Envoyer comme note vocale PTT
            const audioBuffer = Buffer.from(response.audio_base64, 'base64');
            sent = await whatsappService.sendVoiceNote(merchantPhone, senderJid, audioBuffer);
            if (sent) logger.info('RÉPONSE VOCALE ENVOYÉE', { to: senderJid, bytes: audioBuffer.length });
        } else {
            sent = await whatsappService.sendMessage(merchantPhone, senderJid, botResponse);
            if (sent) logger.info('RÉPONSE ENVOYÉE', { to: senderJid });
        }

        if (response.images_to_send && response.images_to_send.length > 0) {
            await this._sendImages(merchantPhone, senderJid, response.images_to_send);
        }

        if (response.send_location && response.merchant_location) {
            const loc = response.merchant_location;
            if (loc.latitude && loc.longitude) {
                await whatsappService.sendLocation(merchantPhone, senderJid, {
                    latitude: loc.latitude,
                    longitude: loc.longitude,
                    name: loc.name || 'Ma boutique',
                    address: loc.address || '',
                });
            } else if (loc.address) {
                await whatsappService.sendMessage(
                    merchantPhone, senderJid,
                    `📍 Voici l'adresse de la boutique:\n\n${loc.address}`
                );
            }
        }

        if (response.goodbye_message) {
            await new Promise(resolve => setTimeout(resolve, 800));
            await whatsappService.sendMessage(merchantPhone, senderJid, response.goodbye_message);
        }
    }

    /**
     * Traite une commande marchand
     */
    async handleMerchantCommand(merchantPhone, sock, message) {
        const messageText = this._extractMessageText(message) ||
            message.message?.imageMessage?.caption || '';

        const hasImage = !!message.message?.imageMessage;
        let imagePath = null;

        // Télécharger l'image si présente
        if (hasImage) {
            logger.info('Image marchand détectée', { merchantPhone });
            imagePath = await mediaService.downloadAndSaveImage(sock, message, merchantPhone);

            if (!messageText && !imagePath) return;
        }

        // Ignorer si pas de contenu
        if (!messageText && !imagePath) return;

        // Ignorer les réponses du bot
        if (this._isBotResponse(messageText)) {
            logger.debug('Ignoré: réponse du bot');
            return;
        }

        logger.info('Commande marchand', { merchantPhone, text: messageText, imagePath });

        try {
            const response = await kalgaApiService.sendMerchantCommand({
                merchantPhone,
                message: messageText,
                imagePath,
            });

            // Envoyer la réponse si nécessaire
            if (response.action !== 'unknown' && response.action !== 'ignored') {
                const responseText = response.response;
                if (!responseText || responseText.trim() === '') {
                    logger.debug('Pas de message à envoyer (vide)');
                    return;
                }

                const merchantJid = whatsappService.getMerchantJid(
                    merchantPhone,
                    message.key.remoteJid
                );

                await sock.sendMessage(merchantJid, { text: responseText });
                logger.info('Réponse envoyée au marchand', {
                    merchantPhone,
                    response: responseText.substring(0, 50),
                });
            }

        } catch (error) {
            logger.error('Erreur commande marchand', { error: error.message });

            // Envoyer un message d'erreur au marchand
            const merchantJid = whatsappService.getMerchantJid(
                merchantPhone,
                message.key.remoteJid
            );
            try {
                await sock.sendMessage(merchantJid, {
                    text: "⚠️ Service temporairement indisponible. Réessaie dans quelques instants.",
                });
            } catch (sendErr) {
                logger.error('Impossible d\'envoyer l\'erreur au marchand');
            }
        }
    }

    /**
     * Extrait le texte d'un message et l'enrichit avec le contexte de citation
     */
    _extractMessageText(message) {
        const text = message.message?.conversation ||
            message.message?.extendedTextMessage?.text || '';
        return this._enrichWithQuotedContext(message, text);
    }

    /**
     * Enrichit le texte avec le contexte du message cité (reply WhatsApp)
     * Permet au bot de savoir à quelle photo/variante le client répond
     */
    _enrichWithQuotedContext(message, messageText) {
        const msgContent = message.message;
        if (!msgContent) return messageText;

        // Chercher contextInfo dans tous les types de messages
        let contextInfo = null;
        for (const key of Object.keys(msgContent)) {
            if (msgContent[key]?.contextInfo) {
                contextInfo = msgContent[key].contextInfo;
                break;
            }
        }

        if (!contextInfo?.quotedMessage) return messageText;

        const quoted = contextInfo.quotedMessage;

        // Priorité : caption d'image/vidéo > texte conversation > texte étendu
        const quotedImageCaption = quoted.imageMessage?.caption ||
            quoted.videoMessage?.caption;
        const quotedText = quoted.conversation ||
            quoted.extendedTextMessage?.text;

        if (quotedImageCaption) {
            logger.debug('Citation image détectée', { caption: quotedImageCaption });
            return `[Répond à la photo: "${quotedImageCaption}"] ${messageText}`;
        } else if (quotedText) {
            const preview = quotedText.substring(0, 100);
            logger.debug('Citation texte détectée', { preview });
            return `[Répond à: "${preview}"] ${messageText}`;
        }

        return messageText;
    }

    /**
     * Vérifie si un message cité contient un code produit
     */
    _checkQuotedProductCode(contextInfo) {
        if (!contextInfo?.quotedMessage) return false;
        const quotedText = contextInfo.quotedMessage.conversation ||
            contextInfo.quotedMessage.imageMessage?.caption ||
            contextInfo.quotedMessage.videoMessage?.caption || '';
        return /#K\d{3}/i.test(quotedText);
    }

    /**
     * Extrait le code produit d'un message
     */
    _extractProductCode(message, messageText) {
        // Chercher dans le contexte (message cité)
        let contextInfo = null;
        const msgContent = message.message;

        if (msgContent) {
            for (const key of Object.keys(msgContent)) {
                if (msgContent[key]?.contextInfo) {
                    contextInfo = msgContent[key].contextInfo;
                    break;
                }
            }
        }

        // Chercher dans le message cité
        if (contextInfo?.quotedMessage) {
            const quotedText = contextInfo.quotedMessage.conversation ||
                contextInfo.quotedMessage.extendedTextMessage?.text ||
                contextInfo.quotedMessage.imageMessage?.caption ||
                contextInfo.quotedMessage.videoMessage?.caption || '';

            const codeMatch = quotedText.match(/#K\d{3}/i);
            if (codeMatch) {
                logger.info('Code produit trouvé dans citation', { productCode: codeMatch[0] });
                return codeMatch[0].toUpperCase();
            }
        }

        // Chercher dans le message lui-même
        const codeInMessage = messageText.match(/#K\d{3}/i);
        if (codeInMessage) {
            logger.info('Code produit trouvé dans message', { productCode: codeInMessage[0] });
            return codeInMessage[0].toUpperCase();
        }

        return null;
    }

    /**
     * Vérifie si c'est une réponse automatique du bot
     */
    _isBotResponse(text) {
        if (!text) return false;

        // Vérifier les préfixes emoji
        if (this.botPrefixes.some(prefix => text.startsWith(prefix))) {
            return true;
        }

        // Vérifier les mots-clés
        return this.botKeywords.some(kw => text.includes(kw));
    }

    /**
     * Envoie une liste d'images avec délai entre chaque envoi
     * pour un comportement plus naturel
     */
    async _sendImages(merchantPhone, to, images) {
        logger.info('Images à envoyer', { count: images.length });

        for (let i = 0; i < images.length; i++) {
            const img = images[i];

            // Délai avant chaque image (sauf la première)
            // 2-3 secondes entre chaque image pour paraître naturel
            if (i > 0) {
                const delay = 2000 + Math.random() * 1000; // 2-3 secondes
                await new Promise(resolve => setTimeout(resolve, delay));
            }

            const sent = await whatsappService.sendImage(
                merchantPhone,
                to,
                img.image_path,
                img.caption || ''
            );
            if (sent) {
                logger.info('Image envoyée', { index: i + 1, total: images.length, imagePath: img.image_path });
            }
        }
    }
}

// Instance singleton
const messageService = new MessageService();

module.exports = { MessageService, messageService };
