const express = require('express');
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, makeCacheableSignalKeyStore, downloadMediaMessage } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const pino = require('pino');
require('dotenv').config();

// ========== SYSTÈME DE LOGS ==========
const LOGS_DIR = path.join(__dirname, 'logs');
if (!fs.existsSync(LOGS_DIR)) {
    fs.mkdirSync(LOGS_DIR, { recursive: true });
}

// Fichier de log du jour
function getLogFileName() {
    const now = new Date();
    const date = now.toISOString().split('T')[0]; // YYYY-MM-DD
    return path.join(LOGS_DIR, `whatsapp-${date}.log`);
}

// Fonction pour écrire dans le log
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

// Raccourcis pour les niveaux de log
const LOG = {
    info: (msg, data) => log('INFO', msg, data),
    warn: (msg, data) => log('WARN', msg, data),
    error: (msg, data) => log('ERROR', msg, data),
    debug: (msg, data) => log('DEBUG', msg, data),
    message: (msg, data) => log('MSG', msg, data)
};
// =====================================

// Dossier pour stocker les images uploadées
const UPLOADS_DIR = path.join(__dirname, '..', 'kalga-api', 'uploads');

// Créer le dossier uploads s'il n'existe pas
if (!fs.existsSync(UPLOADS_DIR)) {
    fs.mkdirSync(UPLOADS_DIR, { recursive: true });
}

const app = express();
const PORT = process.env.PORT || 3001;
const KALGA_API_URL = process.env.KALGA_API_URL || 'http://localhost:8001';

app.use(express.json());
app.use(cors());

// Logger silencieux pour Baileys
const logger = pino({ level: 'silent' });

// État des clients WhatsApp (un par marchand)
const clients = new Map();
const clientStatus = new Map();
const reconnectAttempts = new Map(); // Compteur de reconnexions
const MAX_RECONNECT_ATTEMPTS = 5;

// Fonction pour vérifier si un client est prêt (définie tôt car utilisée partout)
function isClientReady(merchantPhone) {
    const status = clientStatus.get(merchantPhone);
    return status && status.ready && status.connected;
}

// Fonction pour simuler un comportement humain (anti-ban)
async function simulateHumanBehavior(sock, messageKey, jid, merchantPhone = null) {
    try {
        LOG.debug('Simulation comportement humain...', { jid });

        // 1. Marquer le message comme lu (ignorer les erreurs)
        try {
            await sock.readMessages([messageKey]);
            LOG.debug('Message marqué comme lu');
        } catch (readErr) {
            // Ignorer silencieusement - parfois ça échoue mais c'est pas grave
        }

        // 2. Petit délai avant de commencer à "taper" (1-2 secondes)
        const initialDelay = 1000 + Math.random() * 1000;
        await new Promise(resolve => setTimeout(resolve, initialDelay));

        // 3. S'abonner à la présence du contact et envoyer "en train d'écrire"
        try {
            // Vérifier que la connexion est toujours active
            if (merchantPhone && !isClientReady(merchantPhone)) {
                LOG.warn('Connexion perdue pendant simulation, skip présence');
            } else {
                await sock.presenceSubscribe(jid);
                await sock.sendPresenceUpdate('composing', jid);
                LOG.debug('Statut "en train d\'écrire" envoyé');
            }
        } catch (presErr) {
            // Ignorer silencieusement
        }

        // 4. Délai aléatoire de 4 à 7 secondes pour simuler la frappe (anti-ban)
        // Réduit de 6-10s à 4-7s pour éviter les déconnexions pendant l'attente
        const typingDelay = 4000 + Math.random() * 3000;
        LOG.info(`Attente ${(typingDelay/1000).toFixed(1)}s avant réponse...`);
        await new Promise(resolve => setTimeout(resolve, typingDelay));

        // 5. Arrêter le statut "en train d'écrire" (ignorer les erreurs)
        try {
            if (merchantPhone && isClientReady(merchantPhone)) {
                await sock.sendPresenceUpdate('paused', jid);
            }
        } catch (pauseErr) {
            // Ignorer silencieusement
        }

        LOG.debug('Simulation terminée, envoi du message...');

    } catch (err) {
        LOG.error('Erreur simulation humaine', { error: err.message });
        // Continuer même en cas d'erreur - le message sera envoyé quand même
    }
}

// Fonction pour télécharger et sauvegarder une image WhatsApp
async function downloadAndSaveImage(sock, message, merchantPhone) {
    try {
        const imageMessage = message.message?.imageMessage;
        if (!imageMessage) {
            LOG.warn('Pas d\'image dans le message', { keys: Object.keys(message.message || {}) });
            return null;
        }

        LOG.info('Téléchargement de l\'image...', { mimetype: imageMessage.mimetype });

        // Télécharger l'image
        const buffer = await downloadMediaMessage(message, 'buffer', {}, {
            logger: console,
            reuploadRequest: sock.updateMediaMessage
        });

        if (!buffer || buffer.length === 0) {
            LOG.error('Buffer vide après téléchargement');
            return null;
        }

        LOG.info('Buffer reçu', { bytes: buffer.length });

        // Générer un nom unique pour l'image
        const timestamp = Date.now();
        const randomId = Math.random().toString(36).substring(2, 8);
        const ext = imageMessage.mimetype?.includes('png') ? 'png' : 'jpg';
        const filename = `${merchantPhone}_${timestamp}_${randomId}.${ext}`;
        const filepath = path.join(UPLOADS_DIR, filename);

        // Vérifier que le dossier existe
        if (!fs.existsSync(UPLOADS_DIR)) {
            LOG.info('Création du dossier uploads', { path: UPLOADS_DIR });
            fs.mkdirSync(UPLOADS_DIR, { recursive: true });
        }

        // Sauvegarder l'image
        fs.writeFileSync(filepath, buffer);
        LOG.info('Image sauvegardée', { filename, bytes: buffer.length });

        // Vérifier que le fichier existe
        if (fs.existsSync(filepath)) {
            LOG.debug('Fichier vérifié', { filepath });
        } else {
            LOG.error('Fichier non créé!');
            return null;
        }

        return filename;
    } catch (error) {
        LOG.error('Erreur téléchargement image', { error: error.message, stack: error.stack });
        return null;
    }
}

// Fonction pour envoyer une image
async function sendImage(sock, to, imagePath, caption = '') {
    // Gérer les JID au format LID (Linked ID) - les garder tels quels
    let jid = to;
    if (!to.includes('@')) {
        jid = `${to}@s.whatsapp.net`;
    } else if (to.includes('@lid')) {
        // LID format - garder tel quel
        jid = to;
    } else if (!to.includes('@s.whatsapp.net')) {
        jid = to.replace(/@.*/, '@s.whatsapp.net');
    }

    try {
        const fullPath = path.join(UPLOADS_DIR, imagePath);
        if (!fs.existsSync(fullPath)) {
            LOG.error('Image non trouvée', { path: fullPath });
            return false;
        }

        const imageBuffer = fs.readFileSync(fullPath);
        await sock.sendMessage(jid, {
            image: imageBuffer,
            caption: caption
        });
        LOG.info('Image envoyée', { imagePath, to: jid });
        return true;
    } catch (error) {
        LOG.error('Erreur envoi image', { error: error.message });
        return false;
    }
}

// Fonction d'envoi de message avec retry et vérification de connexion
async function sendMessage(sock, to, text, merchantPhone = null, retries = 3) {
    // Gérer les JID au format LID (Linked ID) - les garder tels quels
    let jid = to;
    if (!to.includes('@')) {
        jid = `${to}@s.whatsapp.net`;
    } else if (to.includes('@lid')) {
        // LID format - garder tel quel
        jid = to;
    } else if (!to.includes('@s.whatsapp.net')) {
        jid = to.replace(/@.*/, '@s.whatsapp.net');
    }

    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            // Obtenir le socket actuel (peut avoir changé après reconnexion)
            let currentSock = sock;
            if (merchantPhone) {
                const freshSock = clients.get(merchantPhone);
                if (freshSock) {
                    currentSock = freshSock;
                }

                // Vérifier la connexion avant d'envoyer
                if (!isClientReady(merchantPhone)) {
                    LOG.warn('Client non prêt, attente reconnexion...', { merchantPhone, attempt });
                    await new Promise(resolve => setTimeout(resolve, 5000));

                    // Récupérer le nouveau socket après reconnexion
                    const newSock = clients.get(merchantPhone);
                    if (newSock && isClientReady(merchantPhone)) {
                        currentSock = newSock;
                        LOG.info('Nouveau socket obtenu après reconnexion');
                    } else {
                        LOG.error('Client toujours non prêt après attente', { merchantPhone });
                        continue;
                    }
                }
            }

            await currentSock.sendMessage(jid, { text });
            LOG.info('Message envoyé', { to: jid, textPreview: text.substring(0, 50) });
            return true;
        } catch (err) {
            LOG.error(`Erreur envoi (tentative ${attempt}/${retries})`, { error: err.message, to: jid });
            if (attempt < retries) {
                // Délai progressif entre les tentatives
                const delay = 3000 * attempt;
                LOG.info(`Attente ${delay/1000}s avant nouvelle tentative...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    return false;
}

// Créer ou récupérer un client WhatsApp pour un marchand
async function getOrCreateClient(merchantPhone) {
    if (clients.has(merchantPhone)) {
        return clients.get(merchantPhone);
    }

    LOG.info('Création client WhatsApp', { merchantPhone });

    // Initialiser le statut
    clientStatus.set(merchantPhone, {
        connected: false,
        ready: false,
        qrCode: null
    });

    const authPath = path.join(process.cwd(), 'sessions', `baileys-${merchantPhone}`);

    const startSocket = async () => {
        const { state, saveCreds } = await useMultiFileAuthState(authPath);

        const sock = makeWASocket({
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, logger)
            },
            printQRInTerminal: false,
            logger,
            browser: ['KALGA', 'Chrome', '120.0.0']
        });

        // Sauvegarde des credentials
        sock.ev.on('creds.update', saveCreds);

        // Gestion connexion
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                LOG.info('QR Code généré', { merchantPhone });
                qrcode.generate(qr, { small: true });
                const status = clientStatus.get(merchantPhone);
                status.qrCode = qr;
                status.connected = false;
                status.ready = false;
            }

            if (connection === 'open') {
                LOG.info('WhatsApp CONNECTÉ', { merchantPhone });
                const status = clientStatus.get(merchantPhone);
                status.ready = true;
                status.connected = true;
                status.qrCode = null;
                // Réinitialiser le compteur de reconnexions
                reconnectAttempts.delete(merchantPhone);
            }

            if (connection === 'close') {
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

                LOG.warn('WhatsApp DÉCONNECTÉ', { merchantPhone, statusCode });

                const status = clientStatus.get(merchantPhone);
                status.connected = false;
                status.ready = false;

                // Gérer les reconnexions avec limite
                const attempts = (reconnectAttempts.get(merchantPhone) || 0) + 1;
                reconnectAttempts.set(merchantPhone, attempts);

                if (shouldReconnect && attempts <= MAX_RECONNECT_ATTEMPTS) {
                    const delay = Math.min(attempts * 5000, 30000); // 5s, 10s, 15s... max 30s
                    LOG.info('Tentative de reconnexion', { merchantPhone, attempt: attempts, maxAttempts: MAX_RECONNECT_ATTEMPTS, delaySeconds: delay/1000 });
                    clients.delete(merchantPhone);
                    setTimeout(() => getOrCreateClient(merchantPhone), delay);
                } else if (attempts > MAX_RECONNECT_ATTEMPTS) {
                    LOG.error('Trop de tentatives de reconnexion - ARRÊT', { merchantPhone });
                    clients.delete(merchantPhone);
                    reconnectAttempts.delete(merchantPhone);
                } else {
                    LOG.warn('Déconnexion définitive (logout)', { merchantPhone });
                    clients.delete(merchantPhone);
                    reconnectAttempts.delete(merchantPhone);
                }
            }
        });

        // === KALGA: Réception des messages ===
        sock.ev.on('messages.upsert', async ({ messages, type }) => {
            if (type !== 'notify') return;

            for (const message of messages) {
                try {
                    const remoteJid = message.key.remoteJid;
                    const fromMe = message.key.fromMe;
                    const messageText = message.message?.conversation ||
                                       message.message?.extendedTextMessage?.text || '';

                    LOG.message('MESSAGE REÇU', {
                        merchantPhone,
                        remoteJid,
                        fromMe,
                        text: messageText.substring(0, 80)
                    });

                    // Messages envoyés par le marchand (fromMe = true)
                    if (fromMe) {
                        // Vérifier si c'est une commande marchand (texte ou image)
                        const hasImage = !!message.message?.imageMessage;
                        const hasText = !!messageText || !!message.message?.imageMessage?.caption;

                        if (hasText || hasImage) {
                            LOG.info('Commande marchand détectée', { hasText, hasImage });
                            await handleMerchantCommand(sock, merchantPhone, message);
                        }
                        continue;
                    }

                    // Ignorer les messages de groupe
                    if (message.key.remoteJid.includes('@g.us')) {
                        LOG.debug('Message de groupe ignoré');
                        continue;
                    }

                    // Ignorer status@broadcast
                    if (message.key.remoteJid === 'status@broadcast') {
                        LOG.debug('Message status@broadcast ignoré');
                        continue;
                    }

                    // messageText déjà extrait plus haut
                    // Garder le remoteJid complet pour l'envoi (peut être @lid ou @s.whatsapp.net)
                    const senderJid = message.key.remoteJid;
                    // Extraire le numéro/ID pour l'API (enlever @s.whatsapp.net ou @lid)
                    const senderPhone = message.key.remoteJid.replace(/@.*/, '');

                    // Détecter les messages vocaux/audio
                    const isVoiceMessage = !!message.message?.audioMessage;

                    if (isVoiceMessage) {
                        LOG.info('Message vocal détecté', { senderPhone });

                        // Vérifier si le vocal cite un Status avec code produit
                        let hasProductCode = false;
                        const audioContextInfo = message.message?.audioMessage?.contextInfo;
                        if (audioContextInfo?.quotedMessage) {
                            const quotedText = audioContextInfo.quotedMessage.conversation ||
                                              audioContextInfo.quotedMessage.imageMessage?.caption ||
                                              audioContextInfo.quotedMessage.videoMessage?.caption || '';
                            if (quotedText.match(/#K\d{3}/i)) {
                                hasProductCode = true;
                            }
                        }

                        // Ne répondre que si c'est une réponse à un produit (Status avec code)
                        if (hasProductCode) {
                            await simulateHumanBehavior(sock, message.key, senderJid, merchantPhone);
                            await sendMessage(sock, senderJid, "Désolé, je ne peux pas écouter les vocaux. Écris-moi en texte stp", merchantPhone);
                        } else {
                            LOG.debug('Vocal ignoré (pas de code produit)');
                        }
                        continue;
                    }

                    // Si pas de texte et pas de vocal, ignorer
                    if (!messageText) {
                        LOG.debug('Message sans texte ignoré');
                        continue;
                    }

                    // Ignorer si l'expéditeur est le marchand lui-même
                    if (senderPhone === merchantPhone) {
                        LOG.debug('Message du marchand à lui-même ignoré');
                        continue;
                    }

                    LOG.message('MESSAGE CLIENT', {
                        merchantPhone,
                        clientPhone: senderPhone,
                        text: messageText
                    });

                    // Extraire le code produit du message cité (Status ou message normal)
                    let productCode = null;

                    // Chercher contextInfo dans TOUS les types de messages possibles
                    let contextInfo = null;
                    const msgContent = message.message;

                    if (msgContent) {
                        // Parcourir tous les types de messages pour trouver contextInfo
                        for (const key of Object.keys(msgContent)) {
                            if (msgContent[key]?.contextInfo) {
                                contextInfo = msgContent[key].contextInfo;
                                LOG.debug('ContextInfo trouvé', { key });
                                break;
                            }
                        }
                    }

                    const quotedMessage = contextInfo?.quotedMessage;

                    if (quotedMessage) {
                        // Essayer plusieurs formats de message cité
                        let quotedText = quotedMessage.conversation ||
                                        quotedMessage.extendedTextMessage?.text ||
                                        quotedMessage.imageMessage?.caption ||
                                        quotedMessage.videoMessage?.caption ||
                                        '';

                        LOG.debug('Message cité trouvé', { quotedText: quotedText.substring(0, 80) });

                        const codeMatch = quotedText.match(/#K\d{3}/i);
                        if (codeMatch) {
                            productCode = codeMatch[0].toUpperCase();
                            LOG.info('Code produit trouvé dans citation', { productCode });
                        }
                    }

                    // Aussi chercher le code dans le message lui-même
                    if (!productCode) {
                        const codeInMessage = messageText.match(/#K\d{3}/i);
                        if (codeInMessage) {
                            productCode = codeInMessage[0].toUpperCase();
                            LOG.info('Code produit trouvé dans message', { productCode });
                        }
                    }

                    // Appeler l'API KALGA
                    LOG.info('Envoi à KALGA API', { merchantPhone, clientPhone: senderPhone, productCode });

                    // Limiter la taille du message (protection anti-spam et coût API)
                    const MAX_MESSAGE_LENGTH = 2000;
                    const truncatedMessage = messageText.length > MAX_MESSAGE_LENGTH
                        ? messageText.substring(0, MAX_MESSAGE_LENGTH)
                        : messageText;

                    const response = await axios.post(`${KALGA_API_URL}/api/chat/incoming`, {
                        merchant_phone: merchantPhone,
                        client_phone: senderPhone,
                        message: truncatedMessage,
                        product_code: productCode
                    }, {
                        timeout: 30000,
                        headers: { 'Content-Type': 'application/json' }
                    });

                    // Vérifier si on doit répondre
                    if (response.data.no_response) {
                        LOG.warn('PAS DE RÉPONSE - conversation terminée ou pas de contexte', { senderPhone });
                        continue;
                    }

                    const botResponse = response.data.message;

                    // Ne pas envoyer de message vide
                    if (!botResponse || botResponse.trim() === '') {
                        LOG.warn('MESSAGE VIDE reçu de l\'API', { senderPhone });
                        continue;
                    }

                    LOG.info('Réponse KALGA reçue', { response: botResponse.substring(0, 60) });

                    // Simuler comportement humain avant de répondre (anti-ban)
                    // senderJid est déjà défini plus haut (remoteJid complet avec @lid ou @s.whatsapp.net)
                    await simulateHumanBehavior(sock, message.key, senderJid, merchantPhone);

                    // Envoyer la réponse texte - utiliser senderJid (JID complet) pour l'envoi
                    const sent = await sendMessage(sock, senderJid, botResponse, merchantPhone);
                    if (sent) {
                        LOG.info('RÉPONSE ENVOYÉE', { to: senderJid, response: botResponse.substring(0, 50) });
                    } else {
                        LOG.error('ÉCHEC ENVOI RÉPONSE', { to: senderJid });
                    }

                    // Envoyer les images si présentes (variantes de couleur)
                    if (response.data.images_to_send && response.data.images_to_send.length > 0) {
                        LOG.info('Images à envoyer', { count: response.data.images_to_send.length });
                        for (const img of response.data.images_to_send) {
                            // Petit délai entre les images
                            await new Promise(resolve => setTimeout(resolve, 1500));
                            const imageSent = await sendImage(sock, senderJid, img.image_path, img.caption || '');
                            if (imageSent) {
                                LOG.info('Image envoyée', { imagePath: img.image_path });
                            }
                        }
                    }

                } catch (error) {
                    LOG.error('ERREUR traitement message', { error: error.message, stack: error.stack });
                }
            }
        });

        clients.set(merchantPhone, sock);
        return sock;
    };

    return startSocket();
}

// Gestion des commandes marchand
async function handleMerchantCommand(sock, merchantPhone, message) {
    try {
        // Récupérer le texte du message (peut être dans différents endroits)
        let messageText = message.message?.conversation ||
                           message.message?.extendedTextMessage?.text ||
                           message.message?.imageMessage?.caption || '';

        // Vérifier s'il y a une image
        const hasImage = !!message.message?.imageMessage;
        let imagePath = null;

        if (hasImage) {
            LOG.info('Image marchand détectée', { merchantPhone });
            imagePath = await downloadAndSaveImage(sock, message, merchantPhone);

            // Si l'image n'a pas de caption et qu'on est en session de création,
            // on traite l'image comme réponse à l'étape en cours
            if (!messageText && imagePath) {
                LOG.debug('Image sans texte - utilisation comme réponse de session');
                messageText = '';  // Message vide mais on a l'image
            }
        }

        // Si pas de texte et pas d'image valide, ignorer
        if (!messageText && !imagePath) return;

        // Ignorer les réponses du bot (éviter boucle infinie)
        const botResponsePrefixes = ['📦', '✅', '📋', '🛒', '🏷️', '💰', '💵', '👉', '❌', '⚠️', '⏳', '🔧', '📸'];
        const botResponseKeywords = [
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
            'passe au magasin'
        ];

        if (messageText) {
            // Vérifier les préfixes emoji
            if (botResponsePrefixes.some(prefix => messageText.startsWith(prefix))) {
                LOG.debug('Ignoré: réponse du bot (préfixe)');
                return;
            }
            // Vérifier les mots-clés du bot
            if (botResponseKeywords.some(kw => messageText.includes(kw))) {
                LOG.debug('Ignoré: réponse du bot (mot-clé)');
                return;
            }
        }

        LOG.info('Commande marchand', { merchantPhone, text: messageText, imagePath });

        // Appeler l'API pour traiter la commande
        let response;
        try {
            response = await axios.post(`${KALGA_API_URL}/api/merchant/command`, {
                merchant_phone: merchantPhone,
                message: messageText,
                image_path: imagePath  // Nouveau champ pour l'image
            }, {
                timeout: 30000,
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (apiErr) {
            LOG.error('Erreur API commande marchand', {
                error: apiErr.message,
                status: apiErr.response?.status,
                data: apiErr.response?.data
            });
            // Envoyer un message d'erreur au marchand
            // Utiliser le remoteJid ou construire avec le code pays
            let errorJid = message.key.remoteJid;
            if (errorJid.includes('@lid')) {
                // LID n'est pas utilisable, construire le JID
                if (sock.user && sock.user.id) {
                    errorJid = sock.user.id.replace(/:.*/, '') + '@s.whatsapp.net';
                } else {
                    const fullNumber = merchantPhone.startsWith('0')
                        ? '225' + merchantPhone.substring(1)
                        : (merchantPhone.startsWith('225') ? merchantPhone : '225' + merchantPhone);
                    errorJid = `${fullNumber}@s.whatsapp.net`;
                }
            }
            try {
                await sock.sendMessage(errorJid, {
                    text: "⚠️ Service temporairement indisponible. Réessaie dans quelques instants."
                });
            } catch (sendErr) {
                LOG.error('Impossible d\'envoyer l\'erreur au marchand', { error: sendErr.message });
            }
            return;
        }

        LOG.info('Réponse API commande', { action: response.data.action });

        // Envoyer la réponse si c'est une commande reconnue ET qu'il y a un message à envoyer
        if (response.data.action !== 'unknown' && response.data.action !== 'ignored') {
            const responseText = response.data.response;

            // Ne pas envoyer de message vide
            if (!responseText || responseText.trim() === '') {
                LOG.debug('Pas de message à envoyer (vide)');
                return;
            }

            // IMPORTANT: Utiliser le remoteJid original quand c'est le marchand lui-même
            let merchantJid = message.key.remoteJid;

            // Si le remoteJid n'est pas le marchand, construire le JID
            const remoteNumber = message.key.remoteJid.replace('@s.whatsapp.net', '').replace('@lid', '');
            if (!remoteNumber.includes(merchantPhone) && !remoteNumber.endsWith(merchantPhone)) {
                if (sock.user && sock.user.id) {
                    merchantJid = sock.user.id.replace(/:.*/, '') + '@s.whatsapp.net';
                } else {
                    const fullNumber = merchantPhone.startsWith('0')
                        ? '225' + merchantPhone.substring(1)
                        : (merchantPhone.startsWith('225') ? merchantPhone : '225' + merchantPhone);
                    merchantJid = `${fullNumber}@s.whatsapp.net`;
                }
            }

            try {
                await sock.sendMessage(merchantJid, { text: responseText });
                LOG.info('Réponse envoyée au marchand', { merchantPhone, response: responseText.substring(0, 50) });
            } catch (sendErr) {
                LOG.error('Échec envoi au marchand', { error: sendErr.message });
            }
        } else if (response.data.action === 'ignored') {
            LOG.debug('Action ignorée (image dupliquée, etc.)');
        } else {
            LOG.debug('Commande non reconnue, pas de réponse');
        }

    } catch (error) {
        LOG.error('Erreur commande marchand', { error: error.message, stack: error.stack });
    }
}

// === ROUTES API ===

// Page d'accueil
app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>KALGA WhatsApp Bridge</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
                h1 { color: #25d366; }
                .links { margin: 30px 0; }
                .links a {
                    display: inline-block;
                    margin: 10px;
                    padding: 10px 20px;
                    background: #25d366;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>KALGA WhatsApp Bridge (Baileys)</h1>
            <p>Service de connexion WhatsApp pour marchands</p>
            <div class="links">
                <a href="/status">Statut</a>
                <a href="/docs">Documentation</a>
            </div>
            <p>Port: ${PORT}</p>
        </body>
        </html>
    `);
});

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// Statut global
app.get('/status', (req, res) => {
    const statuses = {};
    for (const [phone, status] of clientStatus.entries()) {
        statuses[phone] = status;
    }
    res.json({
        service: 'kalga-whatsapp-bridge-baileys',
        merchants_connected: clients.size,
        uptime: process.uptime(),
        statuses
    });
});

// Connecter un marchand
app.post('/connect', async (req, res) => {
    const { merchant_phone } = req.body;

    if (!merchant_phone) {
        return res.status(400).json({ error: 'merchant_phone requis' });
    }

    try {
        await getOrCreateClient(merchant_phone);

        res.json({
            success: true,
            message: `Client WhatsApp initialisé pour ${merchant_phone}`,
            status: clientStatus.get(merchant_phone)
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// QR Code pour un marchand
app.get('/qr/:merchant_phone', (req, res) => {
    const { merchant_phone } = req.params;
    const status = clientStatus.get(merchant_phone);

    if (!status) {
        return res.status(404).json({ error: 'Marchand non trouvé. Utilisez POST /connect d\'abord.' });
    }

    if (status.ready) {
        res.send(`
            <html>
            <head><title>KALGA - ${merchant_phone}</title></head>
            <body style="font-family: Arial; text-align: center; margin: 50px;">
                <h1 style="color: #25d366;">✅ Déjà connecté!</h1>
                <p>WhatsApp pour ${merchant_phone} est prêt.</p>
            </body>
            </html>
        `);
    } else if (status.qrCode) {
        // Générer QR en ASCII
        let qrAscii = '';
        const originalWrite = process.stdout.write.bind(process.stdout);
        process.stdout.write = (chunk) => { qrAscii += chunk; return true; };
        qrcode.generate(status.qrCode, { small: true });
        process.stdout.write = originalWrite;

        res.send(`
            <html>
            <head>
                <title>KALGA QR - ${merchant_phone}</title>
                <meta http-equiv="refresh" content="10">
                <style>
                    body { font-family: Arial; text-align: center; margin: 20px; }
                    .qr { font-family: monospace; font-size: 6px; line-height: 6px; white-space: pre; }
                </style>
            </head>
            <body>
                <h1 style="color: #25d366;">Scanner le QR Code</h1>
                <p>Marchand: ${merchant_phone}</p>
                <pre class="qr">${qrAscii}</pre>
                <p>Page auto-refresh toutes les 10s</p>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <html>
            <head>
                <title>KALGA - ${merchant_phone}</title>
                <meta http-equiv="refresh" content="5">
            </head>
            <body style="font-family: Arial; text-align: center; margin: 50px;">
                <h1>⏳ Chargement...</h1>
                <p>QR Code en cours de génération pour ${merchant_phone}</p>
            </body>
            </html>
        `);
    }
});

// Statut d'un marchand
app.get('/status/:merchant_phone', (req, res) => {
    const { merchant_phone } = req.params;
    const status = clientStatus.get(merchant_phone);

    if (!status) {
        return res.status(404).json({ error: 'Marchand non connecté' });
    }

    res.json({
        merchant_phone,
        ...status
    });
});

// Envoyer un message
app.post('/send', async (req, res) => {
    const { merchant_phone, to, message } = req.body;

    if (!merchant_phone || !to || !message) {
        return res.status(400).json({ error: 'merchant_phone, to et message requis' });
    }

    const sock = clients.get(merchant_phone);
    const status = clientStatus.get(merchant_phone);

    if (!sock || !status?.ready) {
        return res.status(503).json({ error: 'Client WhatsApp non prêt' });
    }

    try {
        const sent = await sendMessage(sock, to, message);
        if (sent) {
            res.json({ success: true, to, message: message.substring(0, 50) + '...' });
        } else {
            res.status(500).json({ error: 'Failed to send message' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Envoyer une image
app.post('/send-image', async (req, res) => {
    const { merchant_phone, to, image_path, caption } = req.body;

    if (!merchant_phone || !to || !image_path) {
        return res.status(400).json({ error: 'merchant_phone, to et image_path requis' });
    }

    const sock = clients.get(merchant_phone);
    const status = clientStatus.get(merchant_phone);

    if (!sock || !status?.ready) {
        return res.status(503).json({ error: 'Client WhatsApp non prêt' });
    }

    try {
        const sent = await sendImage(sock, to, image_path, caption || '');
        if (sent) {
            res.json({ success: true, to, image_path });
        } else {
            res.status(500).json({ error: 'Failed to send image' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Envoyer une localisation GPS
app.post('/send-location', async (req, res) => {
    const { merchant_phone, to, latitude, longitude, name, address } = req.body;

    if (!merchant_phone || !to || latitude === undefined || longitude === undefined) {
        return res.status(400).json({ error: 'merchant_phone, to, latitude et longitude requis' });
    }

    const sock = clients.get(merchant_phone);
    const status = clientStatus.get(merchant_phone);

    if (!sock || !status?.ready) {
        return res.status(503).json({ error: 'Client WhatsApp non prêt' });
    }

    // Gérer les JID au format LID (Linked ID) - les garder tels quels
    let jid = to;
    if (!to.includes('@')) {
        jid = `${to}@s.whatsapp.net`;
    } else if (to.includes('@lid')) {
        jid = to;
    } else if (!to.includes('@s.whatsapp.net')) {
        jid = to.replace(/@.*/, '@s.whatsapp.net');
    }

    try {
        await sock.sendMessage(jid, {
            location: {
                degreesLatitude: parseFloat(latitude),
                degreesLongitude: parseFloat(longitude),
                name: name || 'Ma boutique',
                address: address || ''
            }
        });
        LOG.info('Localisation envoyée', { to: jid, latitude, longitude });
        res.json({ success: true, to: jid, latitude, longitude });
    } catch (error) {
        LOG.error('Erreur envoi localisation', { error: error.message });
        res.status(500).json({ error: error.message });
    }
});

// Démarrage
app.listen(PORT, () => {
    LOG.info('========================================');
    LOG.info('KALGA WhatsApp Bridge DÉMARRÉ', { port: PORT, apiUrl: KALGA_API_URL });
    LOG.info('Fichier de log', { path: getLogFileName() });
    LOG.info('========================================');
    console.log(`\n💡 Pour connecter un marchand:`);
    console.log(`   POST /connect { "merchant_phone": "22500000000" }`);
    console.log(`   Puis visiter /qr/22500000000 pour scanner le QR\n`);
});

// Arrêt propre
process.on('SIGINT', async () => {
    LOG.info('Arrêt du bridge...');
    for (const [phone, sock] of clients.entries()) {
        LOG.info('Déconnexion', { phone });
        sock.end();
    }
    process.exit(0);
});

// Gestionnaire d'erreurs global
process.on('uncaughtException', (err) => {
    LOG.error('Erreur non capturée', { error: err.message, stack: err.stack });
    // Ne pas crasher, juste logger
});

process.on('unhandledRejection', (reason, promise) => {
    LOG.error('Promise rejetée', { reason: String(reason) });
    // Ne pas crasher, juste logger
});
