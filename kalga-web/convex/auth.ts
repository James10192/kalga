import { createClient, type GenericCtx } from "@convex-dev/better-auth";
import { convex } from "@convex-dev/better-auth/plugins";
import { betterAuth, type BetterAuthOptions } from "better-auth/minimal";
import { organization, admin, phoneNumber } from "better-auth/plugins";
import { components } from "./_generated/api";
import type { DataModel } from "./_generated/dataModel";
import { query } from "./_generated/server";
import authConfig from "./auth.config";
import authSchema from "./betterAuth/schema";

const siteUrl = process.env.SITE_URL ?? "http://localhost:3000";

// URL du bridge WhatsApp (Node/Baileys). En dev: http://localhost:3001.
const whatsappUrl = process.env.KALGA_WHATSAPP_URL ?? "http://localhost:3001";
// Secret partage entre Convex et le bridge (header X-Internal-Key).
const internalApiKey = process.env.INTERNAL_API_KEY ?? "";
// Session WhatsApp EMETTRICE des OTP, OPTIONNELLE. Il n'existe PAS de numero
// KALGA central : par defaut le sender = le destinataire lui-meme (la propre
// session du marchand, deja `ready`). Cette var permet juste, si on le souhaite,
// de router l'envoi via une session dediee ; vide => fallback sur `to`.
const otpSenderPhone = process.env.KALGA_OTP_SENDER_PHONE ?? "";

/**
 * Envoie l'OTP au marchand via le bridge WhatsApp.
 * Endpoint REEL : POST {KALGA_WHATSAPP_URL}/send (racine, pas /api/send).
 * Payload : { merchant_phone, to, message }, header X-Internal-Key.
 * - merchant_phone = session EMETTRICE = `otpSenderPhone || to` (par defaut la
 *   propre session du marchand ; pas de numero KALGA central), doit etre `ready`
 * - to = destinataire (le marchand qui s'authentifie)
 * Numeros = chiffres uniquement, format international sans `+`.
 *
 * Leve une erreur explicite si l'envoi echoue (pas d'echec silencieux).
 * TODO(plan 003 maintenance) : fallback email OTP quand le bridge est down.
 */
async function sendWhatsappOtp(toPhone: string, code: string): Promise<void> {
  const to = toPhone.replace(/[^\d]/g, "");
  const sender = (otpSenderPhone || to).replace(/[^\d]/g, "");
  if (!sender) {
    throw new Error(
      "Envoi OTP indisponible : aucune session WhatsApp emettrice (KALGA_OTP_SENDER_PHONE)",
    );
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (internalApiKey) {
    headers["X-Internal-Key"] = internalApiKey;
  }

  let res: Response;
  try {
    res = await fetch(`${whatsappUrl}/send`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        merchant_phone: sender,
        to,
        message: `Votre code KALGA : ${code}. Valable 5 minutes.`,
      }),
    });
  } catch (err) {
    throw new Error(
      `Envoi OTP indisponible : bridge WhatsApp injoignable (${
        err instanceof Error ? err.message : String(err)
      })`,
    );
  }

  if (!res.ok) {
    // 503 = session emettrice pas `ready` ; 401 = X-Internal-Key invalide.
    throw new Error(`Envoi OTP indisponible : bridge WhatsApp a repondu ${res.status}`);
  }
}

// Client du composant Better Auth. En LOCAL install on passe le schema local
// en 2e generic + l'option `local`.
export const authComponent = createClient<DataModel, typeof authSchema>(
  components.betterAuth,
  {
    local: {
      schema: authSchema,
    },
  },
);

/**
 * Options Better Auth (plugins, emailAndPassword, etc.) SANS la `database`.
 * Extrait separement pour pouvoir generer l'API adapter du composant local
 * (`createApi`) sans declencher les erreurs d'env vars manquantes au moment
 * de la generation.
 */
export const createAuthOptions = (_ctx: GenericCtx<DataModel>) =>
  ({
    baseURL: siteUrl,
    trustedOrigins: ["http://localhost:3000", siteUrl],

    // Champ session/user expose au scoping multi-tenant. `input: false` : le
    // client ne peut pas le poser, c'est le plugin organization qui le gere.
    user: {
      additionalFields: {
        activeOrganizationId: { type: "string", required: false, input: false },
      },
    },

    // Email + mot de passe (admin back-office, fallback). UI d'ajout en 006.
    emailAndPassword: {
      enabled: true,
      requireEmailVerification: false,
      minPasswordLength: 8,
    },

    plugins: [
      // --- Multi-tenant : chaque boutique = une organization ---
      organization({
        allowUserToCreateOrganization: true,
        creatorRole: "owner",
        membershipLimit: 100,
        invitationExpiresIn: 60 * 60 * 24 * 7, // 7 jours
      }),

      // --- Back-office global + impersonation ---
      admin({
        defaultRole: "user",
        adminRoles: ["admin"],
      }),

      // --- Login par numero WhatsApp + OTP ---
      phoneNumber({
        // cree un user a la premiere verif reussie d'un numero inconnu
        signUpOnVerification: {
          getTempEmail: (phone) => `${phone.replace(/[^\d]/g, "")}@kalga.local`,
          getTempName: (phone) => phone,
        },
        sendOTP: async ({ phoneNumber: phone, code }) => {
          await sendWhatsappOtp(phone, code);
        },
      }),

      // --- Plugin Convex : OBLIGATOIRE, doit etre en DERNIER ---
      convex({
        authConfig,
        jwt: {
          // injecte activeOrganizationId dans le JWT pour le scoping multi-tenant.
          // sessionId et iat sont ajoutes automatiquement, ne pas les redefinir.
          definePayload: ({ user, session }) => ({
            email: user.email,
            name: user.name,
            phoneNumber: (user as { phoneNumber?: string }).phoneNumber ?? null,
            role: (user as { role?: string }).role ?? "user",
            // activeOrganizationId vit sur la SESSION (pose par le plugin organization)
            activeOrganizationId:
              (session as { activeOrganizationId?: string })
                .activeOrganizationId ?? null,
          }),
        },
      }),
    ],
  }) satisfies BetterAuthOptions;

export const createAuth = (ctx: GenericCtx<DataModel>) =>
  betterAuth({
    database: authComponent.adapter(ctx),
    ...createAuthOptions(ctx),
  });

// Utilitaire : user courant (valide la session, null si absent).
export const getCurrentUser = query({
  args: {},
  handler: async (ctx) => authComponent.safeGetAuthUser(ctx),
});
