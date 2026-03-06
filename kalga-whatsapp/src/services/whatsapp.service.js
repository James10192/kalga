/**
 * Service principal WhatsApp
 * Gère les connexions, l'envoi de messages et la gestion des clients
 */
const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    makeCacheableSignalKeyStore,
    Browsers,
    fetchLatestWaWebVersion,
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const path = require('path');

const { config } = require('../config');
const { logger } = require('../utils/logger');
const { normalizeJid, buildMerchantJid } = require('../utils/jid');
const { mediaService } = require('./media.service');

// Logger silencieux pour Baileys
const pinoLogger = pino({ level: 'silent' });

class WhatsAppService {
    constructor() {
        // État des clients WhatsApp (un par marchand)
        this.clients = new Map();
        this.clientStatus = new Map();
        this.reconnectAttempts = new Map();

        // Cache phone → LID JID (pour envoyer aux bons destinataires)
        // Clé: "merchantPhone:clientPhone", Valeur: JID complet (@lid)
        this.jidCache = new Map();

        // Cache LID → phone number (pour afficher le vrai numéro du client)
        // Clé: LID (ex: "232358099845226"), Valeur: phone (ex: "2250161407534")
        this.lidToPhone = new Map();

        // Callbacks pour les messages
        this.onClientMessage = null;
        this.onMerchantCommand = null;
    }

    /**
     * Enregistre le JID d'un contact dans le cache
     */
    cacheJid(merchantPhone, phone, jid) {
        const key = `${merchantPhone}:${phone}`;
        this.jidCache.set(key, jid);
    }

    /**
     * Résout un LID vers le vrai numéro de téléphone
     * Retourne le numéro original si pas de mapping trouvé
     */
    resolvePhone(phoneOrLid) {
        return this.lidToPhone.get(phoneOrLid) || phoneOrLid;
    }

    /**
     * Résout le meilleur JID pour un numéro de téléphone
     * Utilise le cache LID si disponible, sinon fallback sur @s.whatsapp.net
     */
    resolveJid(merchantPhone, phoneOrJid) {
        // Déjà un JID complet
        if (phoneOrJid && phoneOrJid.includes('@')) {
            return phoneOrJid;
        }

        // Si on envoie au marchand lui-même (notifications), utiliser son JID de session
        if (phoneOrJid === merchantPhone) {
            const merchantJid = this.getMerchantJid(merchantPhone);
            logger.debug('JID marchand (self)', { phone: phoneOrJid, jid: merchantJid });
            return merchantJid;
        }

        // Chercher dans le cache
        const key = `${merchantPhone}:${phoneOrJid}`;
        const cachedJid = this.jidCache.get(key);
        if (cachedJid) {
            logger.debug('JID résolu depuis cache', { phone: phoneOrJid, jid: cachedJid });
            return cachedJid;
        }

        // Fallback: @s.whatsapp.net
        return normalizeJid(phoneOrJid);
    }

    /**
     * Vérifie si un client est prêt à envoyer des messages
     */
    isClientReady(merchantPhone) {
        const status = this.clientStatus.get(merchantPhone);
        return status && status.ready && status.connected;
    }

    /**
     * Récupère le statut d'un client
     */
    getClientStatus(merchantPhone) {
        return this.clientStatus.get(merchantPhone) || null;
    }

    /**
     * Récupère tous les statuts
     */
    getAllStatuses() {
        const statuses = {};
        for (const [phone, status] of this.clientStatus.entries()) {
            statuses[phone] = status;
        }
        return statuses;
    }

    /**
     * Obtient ou crée un client WhatsApp pour un marchand
     */
    async getOrCreateClient(merchantPhone) {
        if (this.clients.has(merchantPhone)) {
            return this.clients.get(merchantPhone);
        }

        logger.info('Création client WhatsApp', { merchantPhone });

        // Initialiser le statut
        this.clientStatus.set(merchantPhone, {
            connected: false,
            ready: false,
            qrCode: null,
        });

        const authPath = path.join(config.sessionsDir, `baileys-${merchantPhone}`);
        return this._startSocket(merchantPhone, authPath);
    }

    /**
     * Démarre un socket WhatsApp
     */
    async _startSocket(merchantPhone, authPath) {
        const { state, saveCreds } = await useMultiFileAuthState(authPath);

        const { version } = await fetchLatestWaWebVersion();
        logger.info('Version WA Web', { merchantPhone, version });

        const sock = makeWASocket({
            version,
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, pinoLogger),
            },
            printQRInTerminal: false,
            logger: pinoLogger,
            browser: Browsers.ubuntu('Chrome'),
        });

        // Sauvegarde des credentials
        sock.ev.on('creds.update', saveCreds);

        // Gestion de la connexion
        sock.ev.on('connection.update', (update) =>
            this._handleConnectionUpdate(merchantPhone, sock, update)
        );

        // Réception des messages
        sock.ev.on('messages.upsert', (data) =>
            this._handleMessagesUpsert(merchantPhone, sock, data)
        );

        // Mapping LID ↔ phone number via contacts
        sock.ev.on('contacts.upsert', (contacts) => {
            for (const contact of contacts) {
                if (contact.lid && contact.phoneNumber) {
                    const lid = contact.lid.replace(/@.*/, '');
                    const phone = contact.phoneNumber.replace(/@.*/, '');
                    this.lidToPhone.set(lid, phone);
                    logger.debug('LID mapping', { lid, phone });
                }
                // Aussi mapper l'id si c'est un LID
                if (contact.id && contact.id.includes('@lid') && contact.phoneNumber) {
                    const lid = contact.id.replace(/@.*/, '');
                    const phone = contact.phoneNumber.replace(/@.*/, '');
                    this.lidToPhone.set(lid, phone);
                }
            }
        });

        sock.ev.on('contacts.update', (contacts) => {
            for (const contact of contacts) {
                if (contact.lid && contact.phoneNumber) {
                    const lid = contact.lid.replace(/@.*/, '');
                    const phone = contact.phoneNumber.replace(/@.*/, '');
                    this.lidToPhone.set(lid, phone);
                }
                if (contact.id && contact.id.includes('@lid') && contact.phoneNumber) {
                    const lid = contact.id.replace(/@.*/, '');
                    const phone = contact.phoneNumber.replace(/@.*/, '');
                    this.lidToPhone.set(lid, phone);
                }
            }
        });

        this.clients.set(merchantPhone, sock);
        return sock;
    }

    /**
     * Gère les mises à jour de connexion
     */
    _handleConnectionUpdate(merchantPhone, sock, update) {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            logger.info('QR Code généré', { merchantPhone });
            const status = this.clientStatus.get(merchantPhone);
            status.qrCode = qr;
            status.connected = false;
            status.ready = false;
        }

        if (connection === 'open') {
            // Extraire le vrai numéro WhatsApp depuis sock.user.id
            let realPhone = null;
            if (sock.user && sock.user.id) {
                realPhone = sock.user.id.replace(/:.*/, '');
            }
            logger.info('WhatsApp CONNECTÉ', { merchantPhone, realPhone });

            const status = this.clientStatus.get(merchantPhone);
            status.ready = true;
            status.connected = true;
            status.qrCode = null;
            status.realPhone = realPhone;
            this.reconnectAttempts.delete(merchantPhone);
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

            logger.warn('WhatsApp DÉCONNECTÉ', { merchantPhone, statusCode });

            const status = this.clientStatus.get(merchantPhone);
            status.connected = false;
            status.ready = false;

            // Gestion de la reconnexion
            const attempts = (this.reconnectAttempts.get(merchantPhone) || 0) + 1;
            this.reconnectAttempts.set(merchantPhone, attempts);

            if (shouldReconnect && attempts <= config.maxReconnectAttempts) {
                const delay = Math.min(
                    attempts * config.reconnectBaseDelay,
                    config.maxReconnectDelay
                );
                logger.info('Tentative de reconnexion', {
                    merchantPhone,
                    attempt: attempts,
                    delaySeconds: delay / 1000,
                });
                this.clients.delete(merchantPhone);
                setTimeout(() => this.getOrCreateClient(merchantPhone), delay);
            } else {
                logger.error('Arrêt des reconnexions', { merchantPhone });
                this.clients.delete(merchantPhone);
                this.reconnectAttempts.delete(merchantPhone);
            }
        }
    }

    /**
     * Gère les messages entrants
     */
    async _handleMessagesUpsert(merchantPhone, sock, { messages, type }) {
        if (type !== 'notify') return;

        for (const message of messages) {
            try {
                await this._processMessage(merchantPhone, sock, message);
            } catch (error) {
                logger.error('Erreur traitement message', {
                    error: error.message,
                    stack: error.stack,
                });
            }
        }
    }

    /**
     * Traite un message individuel
     */
    async _processMessage(merchantPhone, sock, message) {
        const remoteJid = message.key.remoteJid;
        const fromMe = message.key.fromMe;
        const messageText = message.message?.conversation ||
            message.message?.extendedTextMessage?.text || '';

        // Tenter de résoudre LID → phone via le store Baileys
        if (remoteJid && remoteJid.includes('@lid')) {
            const lid = remoteJid.replace(/@.*/, '');
            if (!this.lidToPhone.has(lid) && sock.store) {
                try {
                    const contacts = sock.store.contacts || {};
                    const contact = contacts[remoteJid];
                    if (contact && contact.phoneNumber) {
                        const phone = contact.phoneNumber.replace(/@.*/, '');
                        this.lidToPhone.set(lid, phone);
                        logger.info('LID résolu via store', { lid, phone });
                    }
                } catch (e) {
                    // Silencieux
                }
            }
        }

        logger.message('MESSAGE REÇU', {
            merchantPhone,
            remoteJid,
            fromMe,
            text: messageText.substring(0, 80),
        });

        // Message du marchand
        if (fromMe) {
            const hasImage = !!message.message?.imageMessage;
            const hasText = !!messageText || !!message.message?.imageMessage?.caption;

            if ((hasText || hasImage) && this.onMerchantCommand) {
                await this.onMerchantCommand(merchantPhone, sock, message);
            }
            return;
        }

        // Ignorer groupes et status broadcast
        if (remoteJid.includes('@g.us') || remoteJid === 'status@broadcast') {
            logger.debug('Message ignoré (groupe ou broadcast)');
            return;
        }

        // Mettre en cache le JID du client (phone → @lid ou @s.whatsapp.net)
        const clientPhone = remoteJid.replace(/@.*/, '');
        this.cacheJid(merchantPhone, clientPhone, remoteJid);

        // Message client
        if (this.onClientMessage) {
            await this.onClientMessage(merchantPhone, sock, message);
        }
    }

    /**
     * Envoie un message texte
     */
    async sendMessage(merchantPhone, to, text, retries = 3) {
        const jid = this.resolveJid(merchantPhone, to);

        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                let sock = this.clients.get(merchantPhone);

                if (!this.isClientReady(merchantPhone)) {
                    logger.warn('Client non prêt, attente...', { merchantPhone, attempt });
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    sock = this.clients.get(merchantPhone);

                    if (!sock || !this.isClientReady(merchantPhone)) {
                        continue;
                    }
                }

                await sock.sendMessage(jid, { text });
                logger.info('Message envoyé', { to: jid, textPreview: text.substring(0, 50) });
                return true;

            } catch (err) {
                logger.error(`Erreur envoi (tentative ${attempt}/${retries})`, {
                    error: err.message,
                    to: jid,
                });
                if (attempt < retries) {
                    await new Promise(resolve => setTimeout(resolve, 3000 * attempt));
                }
            }
        }
        return false;
    }

    /**
     * Envoie un message vocal PTT (Push-To-Talk)
     * @param {string} merchantPhone
     * @param {string} to - JID destinataire
     * @param {Buffer} audioBuffer - audio OGG/Opus
     * @returns {Promise<boolean>}
     */
    async sendVoiceNote(merchantPhone, to, audioBuffer) {
        const jid = this.resolveJid(merchantPhone, to);

        try {
            const sock = this.clients.get(merchantPhone);
            if (!sock || !this.isClientReady(merchantPhone)) {
                logger.error('Client non prêt pour envoi vocal PTT');
                return false;
            }

            // Waveform synthétique réaliste: 64 valeurs uint8 en courbe sinusoïdale + bruit
            const waveform = Buffer.alloc(64);
            for (let i = 0; i < 64; i++) {
                const sine = Math.sin((i / 64) * Math.PI * 3) * 50 + 50;
                const noise = (Math.random() - 0.5) * 20;
                waveform[i] = Math.max(0, Math.min(255, Math.round(sine + noise)));
            }

            await sock.sendMessage(jid, {
                audio: audioBuffer,
                mimetype: 'audio/ogg; codecs=opus',
                ptt: true,
                waveform,
            });

            logger.info('Vocal PTT envoyé', { to: jid, bytes: audioBuffer.length });
            return true;

        } catch (error) {
            logger.error('Erreur envoi vocal PTT', { error: error.message });
            return false;
        }
    }

    /**
     * Envoie une image
     */
    async sendImage(merchantPhone, to, imagePath, caption = '') {
        const jid = this.resolveJid(merchantPhone, to);

        try {
            const sock = this.clients.get(merchantPhone);
            if (!sock || !this.isClientReady(merchantPhone)) {
                logger.error('Client non prêt pour envoi image');
                return false;
            }

            const imageBuffer = mediaService.readImage(imagePath);
            if (!imageBuffer) {
                return false;
            }

            await sock.sendMessage(jid, { image: imageBuffer, caption });
            logger.info('Image envoyée', { imagePath, to: jid });
            return true;

        } catch (error) {
            logger.error('Erreur envoi image', { error: error.message });
            return false;
        }
    }

    /**
     * Envoie une localisation GPS
     */
    async sendLocation(merchantPhone, to, { latitude, longitude, name, address }) {
        const jid = this.resolveJid(merchantPhone, to);

        try {
            const sock = this.clients.get(merchantPhone);
            if (!sock || !this.isClientReady(merchantPhone)) {
                logger.error('Client non prêt pour envoi localisation');
                return false;
            }

            const lat = parseFloat(latitude);
            const lng = parseFloat(longitude);

            await sock.sendMessage(jid, {
                location: {
                    degreesLatitude: lat,
                    degreesLongitude: lng,
                    name: name || 'Ma boutique',
                    address: address || '',
                    url: `https://www.google.com/maps?q=${lat},${lng}`,
                    accuracyInMeters: 10,
                },
            });
            logger.info('Localisation envoyée', { to: jid, latitude: lat, longitude: lng });
            return true;

        } catch (error) {
            logger.error('Erreur envoi localisation', { error: error.message });
            return false;
        }
    }

    /**
     * Obtient le JID du marchand
     */
    getMerchantJid(merchantPhone, remoteJid = null) {
        const sock = this.clients.get(merchantPhone);

        // Si le remoteJid contient le numéro du marchand, l'utiliser
        if (remoteJid) {
            const remoteNumber = remoteJid.replace(/@.*/, '');
            if (remoteNumber.includes(merchantPhone) || remoteNumber.endsWith(merchantPhone)) {
                return remoteJid;
            }
        }

        return buildMerchantJid(merchantPhone, sock);
    }
}

// Instance singleton
const whatsappService = new WhatsAppService();

module.exports = { WhatsAppService, whatsappService };
