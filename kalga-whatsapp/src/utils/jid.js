/**
 * Utilitaires pour manipuler les JID WhatsApp
 * JID = Jabber ID, identifiant unique des utilisateurs WhatsApp
 */

/**
 * Normalise un numéro de téléphone en JID WhatsApp
 * @param {string} phoneOrJid - Numéro ou JID
 * @returns {string} JID normalisé
 */
function normalizeJid(phoneOrJid) {
    if (!phoneOrJid) return null;

    // Déjà un JID complet avec @lid (Linked ID)
    if (phoneOrJid.includes('@lid')) {
        return phoneOrJid;
    }

    // Déjà un JID complet
    if (phoneOrJid.includes('@s.whatsapp.net')) {
        return phoneOrJid;
    }

    // Numéro de téléphone simple
    if (!phoneOrJid.includes('@')) {
        return `${phoneOrJid}@s.whatsapp.net`;
    }

    // Autre format (@g.us pour groupes, etc.) - normaliser vers s.whatsapp.net
    return phoneOrJid.replace(/@.*/, '@s.whatsapp.net');
}

/**
 * Extrait le numéro de téléphone d'un JID
 * @param {string} jid - JID WhatsApp
 * @returns {string} Numéro de téléphone
 */
function extractPhone(jid) {
    if (!jid) return null;
    return jid.replace(/@.*/, '');
}

/**
 * Vérifie si c'est un JID de groupe
 * @param {string} jid - JID à vérifier
 * @returns {boolean}
 */
function isGroupJid(jid) {
    return jid && jid.includes('@g.us');
}

/**
 * Vérifie si c'est un JID de status broadcast
 * @param {string} jid - JID à vérifier
 * @returns {boolean}
 */
function isStatusBroadcast(jid) {
    return jid === 'status@broadcast';
}

/**
 * Construit un JID marchand à partir de son numéro
 * @param {string} merchantPhone - Numéro du marchand
 * @param {object} sock - Socket WhatsApp (pour obtenir l'ID utilisateur)
 * @returns {string} JID du marchand
 */
function buildMerchantJid(merchantPhone, sock = null) {
    // Si on a le socket, utiliser l'ID utilisateur
    if (sock && sock.user && sock.user.id) {
        return sock.user.id.replace(/:.*/, '') + '@s.whatsapp.net';
    }

    // Sinon, construire à partir du numéro
    let fullNumber = merchantPhone;
    if (merchantPhone.startsWith('0')) {
        fullNumber = '225' + merchantPhone.substring(1);
    } else if (!merchantPhone.startsWith('225')) {
        fullNumber = '225' + merchantPhone;
    }

    return `${fullNumber}@s.whatsapp.net`;
}

module.exports = {
    normalizeJid,
    extractPhone,
    isGroupJid,
    isStatusBroadcast,
    buildMerchantJid,
};
