/**
 * Service métier — établit l'identité de session d'un marchand.
 * Référence : ARCHITECTURE_FRONTEND.md §7.1 (auth) ; modèle réel KALGA
 * (dashboard/static/app.js) : le marchand n'a ni email ni mot de passe — son
 * identité est prouvée par une session WhatsApp CONNECTÉE (vérifiée via le
 * bridge), puis ses données sont chargées par téléphone.
 *
 * Cette fonction est PURE et à dépendances injectées (statut bridge + marchand
 * backend) : aucune dépendance Nitro/réseau, donc testable en isolation avec
 * des fakes (cf. tests/unit/server/merchant-session.test.ts). La couche HTTP
 * (server/api/whatsapp/session.post.ts) injecte les implémentations réelles et
 * pose la session.
 */

/** Statut renvoyé par le bridge WhatsApp pour un numéro (`getClientStatus`). */
export interface BridgeStatus {
  connected: boolean
  ready?: boolean
  realPhone?: string | null
}

/** Marchand tel que renvoyé par le backend `GET /api/merchants/{phone}`. */
export interface MerchantRecord {
  id: number
  phone: string
  business_name: string | null
  is_active: boolean
}

/** Identité de session d'un marchand (pas d'email, pas de JWT backend). */
export interface MerchantSessionUser {
  id: number
  email: null
  role: 'merchant'
  is_active: boolean
  merchant_id: number
  merchant_phone: string
}

/** Dépendances injectées (infra) — permettent de substituer des fakes en test. */
export interface MerchantSessionDeps {
  /** Statut WhatsApp du numéro (bridge). `null` si le bridge ne le connaît pas. */
  getStatus: (phone: string) => Promise<BridgeStatus | null>
  /** Marchand par téléphone (backend). `null` si introuvable. */
  getMerchant: (phone: string) => Promise<MerchantRecord | null>
}

/** Le WhatsApp du numéro n'est pas connecté → on refuse d'ouvrir une session. */
export class WhatsappNotConnectedError extends Error {
  constructor(phone: string) {
    super(`WhatsApp non connecté pour ${phone}`)
    this.name = 'WhatsappNotConnectedError'
  }
}

/** Aucun marchand pour ce numéro côté backend. */
export class MerchantNotFoundError extends Error {
  constructor(phone: string) {
    super(`Marchand introuvable pour ${phone}`)
    this.name = 'MerchantNotFoundError'
  }
}

/**
 * Résout l'identité de session d'un marchand à partir de son téléphone.
 *
 * Règles (sécurité) : on n'ouvre une session QUE si le bridge confirme une
 * session WhatsApp connectée pour ce numéro — vérification SERVEUR, jamais sur
 * la simple affirmation du client. Un marchand suspendu obtient quand même une
 * session (le middleware le redirige vers /account-suspended plutôt que de
 * boucler sur /login).
 */
export async function resolveMerchantSession(
  phone: string,
  deps: MerchantSessionDeps,
): Promise<MerchantSessionUser> {
  const status = await deps.getStatus(phone)
  if (!status?.connected) {
    throw new WhatsappNotConnectedError(phone)
  }

  const merchant = await deps.getMerchant(phone)
  if (!merchant) {
    throw new MerchantNotFoundError(phone)
  }

  return {
    id: merchant.id,
    email: null,
    role: 'merchant',
    is_active: merchant.is_active,
    merchant_id: merchant.id,
    merchant_phone: merchant.phone,
  }
}
