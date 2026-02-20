const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const cors = require('cors');
const path = require('path');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;
const KALGA_API_URL = process.env.KALGA_API_URL || 'http://localhost:8001';

app.use(express.json());
app.use(cors());

// État des clients WhatsApp (un par marchand)
const clients = new Map();
const clientStatus = new Map();

// Configuration Puppeteer
const puppeteerConfig = {
    headless: true,
    args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-extensions'
    ]
};

// Fonction d'envoi de message robuste (contourne le bug markedUnread)
async function sendMessageSafe(client, chatId, text) {
    try {
        // Méthode 1: Injection directe via Puppeteer (plus fiable)
        const result = await client.pupPage.evaluate(async (to, msg) => {
            try {
                // S'assurer que le chatId est au bon format
                const chatWid = to.includes('@') ? to : `${to}@c.us`;

                // Obtenir ou créer le chat
                let chat = await window.Store.Chat.get(chatWid);
                if (!chat) {
                    // Créer le chat si nécessaire
                    const contact = await window.Store.Contact.get(chatWid);
                    if (contact) {
                        chat = await window.Store.Chat.find(chatWid);
                    }
                }

                if (chat) {
                    // Envoyer le message via le Store
                    await window.Store.SendMessage.sendTextMsgToChat(chat, msg);
                    return { success: true };
                } else {
                    return { success: false, error: 'Chat not found' };
                }
            } catch (e) {
                return { success: false, error: e.message };
            }
        }, chatId, text);

        if (result.success) {
            return true;
        }
        throw new Error(result.error || 'Unknown error');
    } catch (err) {
        console.log(`   ⚠️ Méthode 1 échouée: ${err.message}, essai méthode 2...`);

        // Méthode 2: sendMessage standard avec retry
        try {
            await client.sendMessage(chatId, text);
            return true;
        } catch (err2) {
            console.log(`   ⚠️ Méthode 2 échouée: ${err2.message}, essai méthode 3...`);

            // Méthode 3: Via getChat puis send
            try {
                const chat = await client.getChatById(chatId);
                await chat.sendMessage(text);
                return true;
            } catch (err3) {
                console.error(`   ❌ Toutes les méthodes ont échoué: ${err3.message}`);
                return false;
            }
        }
    }
}

// Créer ou récupérer un client WhatsApp pour un marchand
function getOrCreateClient(merchantPhone) {
    if (clients.has(merchantPhone)) {
        return clients.get(merchantPhone);
    }

    console.log(`\n📱 Création client WhatsApp pour marchand: ${merchantPhone}`);

    const client = new Client({
        authStrategy: new LocalAuth({
            clientId: `kalga-${merchantPhone}`,
            dataPath: path.join(process.cwd(), 'sessions')
        }),
        puppeteer: puppeteerConfig
    });

    // Initialiser le statut
    clientStatus.set(merchantPhone, {
        connected: false,
        ready: false,
        qrCode: null
    });

    // QR Code
    client.on('qr', (qr) => {
        console.log(`📱 QR Code pour ${merchantPhone}:`);
        qrcode.generate(qr, { small: true });
        clientStatus.get(merchantPhone).qrCode = qr;
        clientStatus.get(merchantPhone).connected = false;
    });

    // Prêt
    client.on('ready', () => {
        console.log(`✅ WhatsApp connecté pour ${merchantPhone}`);
        const status = clientStatus.get(merchantPhone);
        status.ready = true;
        status.connected = true;
        status.qrCode = null;
    });

    // Déconnexion
    client.on('disconnected', (reason) => {
        console.log(`❌ WhatsApp déconnecté (${merchantPhone}):`, reason);
        const status = clientStatus.get(merchantPhone);
        status.connected = false;
        status.ready = false;
    });

    // === KALGA: Réception des messages ===
    // Utiliser 'message' pour les messages entrants des clients
    client.on('message', async (message) => {
        try {
            // Ignorer les messages de groupe
            if (message.from.includes('@g.us')) {
                return;
            }

            // Ignorer les messages de status@broadcast (réactions aux Status)
            if (message.from === 'status@broadcast') {
                console.log(`📎 Message status@broadcast ignoré`);
                return;
            }

            // Accepter les messages texte ET les images/vidéos avec caption (réponses aux Status)
            const messageText = message.body || '';

            if (message.type !== 'chat' && !messageText) {
                console.log(`📎 Message non-texte sans texte ignoré (type: ${message.type})`);
                return;
            }

            const senderPhone = message.from.replace('@c.us', '');

            // === MESSAGE CLIENT ===
            console.log(`\n📩 [${merchantPhone}] Message de ${senderPhone}:`);
            console.log(`   "${messageText}"`);

            // Extraire le code produit du message cité (réponse à un Status)
            let productCode = null;
            let quotedText = '';

            if (message.hasQuotedMsg) {
                try {
                    const quotedMsg = await message.getQuotedMessage();
                    quotedText = quotedMsg.body || '';
                    console.log(`   📋 Message cité: "${quotedText.substring(0, 50)}..."`);

                    // Chercher #K001, #K002, etc. dans le Status cité
                    const codeMatch = quotedText.match(/#K\d{3}/i);
                    if (codeMatch) {
                        productCode = codeMatch[0].toUpperCase();
                        console.log(`   🏷️ Code produit trouvé dans Status: ${productCode}`);
                    }
                } catch (e) {
                    console.log(`   ⚠️ Impossible de lire le message cité`);
                }
            }

            // Appeler l'API KALGA
            console.log(`🛒 Envoi à KALGA API...`);

            const response = await axios.post(`${KALGA_API_URL}/api/chat/incoming`, {
                merchant_phone: merchantPhone,
                client_phone: senderPhone,
                message: messageText,
                product_code: productCode  // Code extrait du Status cité
            }, {
                timeout: 30000,
                headers: { 'Content-Type': 'application/json' }
            });

            const botResponse = response.data.message;

            console.log(`✅ Réponse KALGA: "${botResponse.substring(0, 50)}..."`);

            // Envoyer la réponse avec la fonction robuste
            const sent = await sendMessageSafe(client, message.from, botResponse);
            if (sent) {
                console.log(`📤 Réponse envoyée à ${senderPhone}`);
            } else {
                console.log(`❌ Échec envoi réponse à ${senderPhone}`);
            }

            // Notifier le marchand si nécessaire
            if (response.data.should_notify_merchant && response.data.notification_reason) {
                console.log(`🔔 Notification marchand: ${response.data.notification_reason}`);
            }

        } catch (error) {
            console.error('❌ Erreur traitement message:', error.message);
        }
    });

    // === COMMANDES MARCHAND (messages envoyés par le marchand lui-même) ===
    client.on('message_create', async (message) => {
        try {
            // Seulement traiter les messages du marchand lui-même
            if (!message.fromMe) {
                return;
            }

            // Ignorer les messages de groupe
            if (message.to && message.to.includes('@g.us')) {
                return;
            }

            const messageText = message.body || '';
            if (!messageText) {
                return;
            }

            // Ignorer les réponses du bot (messages qui commencent par des emojis)
            const botResponsePrefixes = ['📦', '✅', '📋', '🛒', '🏷️', '💰', '💵', '👉', '❌', '⚠️'];
            const isBotResponse = botResponsePrefixes.some(prefix => messageText.startsWith(prefix));
            if (isBotResponse) {
                return;
            }

            // Vérifier si c'est une commande marchand
            const merchantCommands = ['produit', 'nouveau', 'ajouter', 'mes produits', 'liste', 'supprimer', 'aide', 'help', '/produit', '/liste', 'annuler', 'passer', 'skip'];
            const isCommand = merchantCommands.some(cmd => messageText.toLowerCase().startsWith(cmd));

            // Appeler l'API pour vérifier si on est en session ou si c'est une commande
            const response = await axios.post(`${KALGA_API_URL}/api/merchant/command`, {
                merchant_phone: merchantPhone,
                message: messageText
            }, {
                timeout: 30000,
                headers: { 'Content-Type': 'application/json' }
            });

            // Si c'est une commande reconnue ou une session en cours
            if (response.data.action !== 'unknown' || isCommand) {
                console.log(`\n🔧 [${merchantPhone}] Commande marchand:`);
                console.log(`   "${messageText}"`);
                console.log(`   Action: ${response.data.action}`);

                // Envoyer la réponse au marchand avec la fonction robuste
                const merchantChatId = `${merchantPhone}@c.us`;
                const sent = await sendMessageSafe(client, merchantChatId, response.data.response);
                if (sent) {
                    console.log(`📤 Réponse envoyée au marchand`);
                } else {
                    console.log(`❌ Échec envoi réponse au marchand`);
                }
            }

        } catch (error) {
            console.error('❌ Erreur commande marchand:', error.message);
        }
    });

    clients.set(merchantPhone, client);
    return client;
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
            <h1>KALGA WhatsApp Bridge</h1>
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

// Statut global
app.get('/status', (req, res) => {
    const statuses = {};
    for (const [phone, status] of clientStatus.entries()) {
        statuses[phone] = status;
    }
    res.json({
        service: 'kalga-whatsapp-bridge',
        merchants_connected: clients.size,
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
        const client = getOrCreateClient(merchant_phone);

        // Initialiser si pas encore fait
        if (!clientStatus.get(merchant_phone).ready) {
            client.initialize();
        }

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

// Envoyer un message (pour notifications au marchand)
app.post('/send', async (req, res) => {
    const { merchant_phone, to, message } = req.body;

    if (!merchant_phone || !to || !message) {
        return res.status(400).json({ error: 'merchant_phone, to et message requis' });
    }

    const client = clients.get(merchant_phone);
    const status = clientStatus.get(merchant_phone);

    if (!client || !status?.ready) {
        return res.status(503).json({ error: 'Client WhatsApp non prêt' });
    }

    try {
        const chatId = to.includes('@c.us') ? to : `${to}@c.us`;
        const sent = await sendMessageSafe(client, chatId, message);
        if (sent) {
            res.json({ success: true, to, message: message.substring(0, 50) + '...' });
        } else {
            res.status(500).json({ error: 'Failed to send message' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Démarrage
app.listen(PORT, () => {
    console.log(`\n🚀 KALGA WhatsApp Bridge démarré sur port ${PORT}`);
    console.log(`📍 API KALGA: ${KALGA_API_URL}`);
    console.log(`\n💡 Pour connecter un marchand:`);
    console.log(`   POST /connect { "merchant_phone": "22500000000" }`);
    console.log(`   Puis visiter /qr/22500000000 pour scanner le QR\n`);
});

// Arrêt propre
process.on('SIGINT', async () => {
    console.log('\n🛑 Arrêt du bridge...');
    for (const [phone, client] of clients.entries()) {
        console.log(`   Déconnexion ${phone}...`);
        await client.destroy();
    }
    process.exit(0);
});
