/**
 * Agrégation de rafales + sérialisation par conversation.
 *
 * Sur WhatsApp, les clients écrivent en rafale (« Je suis intéressé je peux
 * avoir le prix » puis « Et des photos » 2 s plus tard — vu en production le
 * 2026-06-11 15:20). Traiter chaque message isolément produit des réponses
 * croisées et un contexte coupé en deux.
 *
 * Ce buffer :
 * - regroupe les messages d'un même client arrivés dans une fenêtre courte
 *   (chaque nouveau message prolonge la fenêtre) ;
 * - les livre EN UN SEUL lot à onFlush — le moteur multi-intentions répond
 *   alors une seule fois, de façon cohérente ;
 * - sérialise par conversation : tant qu'un lot est en cours de traitement,
 *   les nouveaux messages patientent pour le lot suivant (plus de croisements).
 *
 * Horloge injectable → testable au runner natif node:test, sans dépendance.
 */
class MessageBuffer {
    /**
     * @param {Object} opts
     * @param {number}   [opts.windowMs=3000]  Fenêtre de rafale (ms)
     * @param {Function} opts.onFlush          async (key, items[]) => void
     * @param {Function} [opts.onError]        (error, key) => void
     * @param {Function} [opts.setTimeoutFn]   Horloge injectable (tests)
     * @param {Function} [opts.clearTimeoutFn]
     */
    constructor({ windowMs = 3000, onFlush, onError = null,
                  setTimeoutFn = setTimeout, clearTimeoutFn = clearTimeout } = {}) {
        if (typeof onFlush !== 'function') {
            throw new Error('MessageBuffer: onFlush est requis');
        }
        this.windowMs = windowMs;
        this.onFlush = onFlush;
        this.onError = onError;
        this._setTimeout = setTimeoutFn;
        this._clearTimeout = clearTimeoutFn;
        this.pending = new Map();    // key -> items[]
        this.timers = new Map();     // key -> timerId
        this.processing = new Set(); // clés dont un lot est en cours
    }

    /** Ajoute un message à la rafale du client et (ré)arme la fenêtre. */
    push(key, item) {
        const items = this.pending.get(key) || [];
        items.push(item);
        this.pending.set(key, items);

        const existing = this.timers.get(key);
        if (existing) this._clearTimeout(existing);
        this.timers.set(key, this._setTimeout(() => this._flush(key), this.windowMs));
    }

    /** Vide immédiatement la rafale (ex. avant de traiter un média, pour l'ordre). */
    async flushNow(key) {
        const timer = this.timers.get(key);
        if (timer) {
            this._clearTimeout(timer);
            this.timers.delete(key);
        }
        await this._flush(key);
    }

    async _flush(key) {
        this.timers.delete(key);
        if (this.processing.has(key)) {
            // Un lot est déjà en cours : la boucle ci-dessous embarquera la suite.
            return;
        }
        this.processing.add(key);
        try {
            // Boucle de sérialisation : tout ce qui arrive PENDANT le traitement
            // forme le lot suivant, traité juste après — jamais en parallèle.
            while (true) {
                const items = this.pending.get(key);
                if (!items || items.length === 0) break;
                this.pending.delete(key);
                try {
                    await this.onFlush(key, items);
                } catch (error) {
                    if (this.onError) this.onError(error, key);
                }
            }
        } finally {
            this.processing.delete(key);
        }
    }
}

module.exports = { MessageBuffer };
