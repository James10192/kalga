import { ConvexError } from "convex/values";

/**
 * Garde server-to-server pour les fonctions internes appelées par le backend
 * Python (FastAPI). Python n'a pas de session utilisateur navigateur : il
 * prouve sa légitimité avec un secret partagé (`INTERNAL_API_KEY`).
 *
 * Chaque fonction `internal.*` reçoit `internalKey: v.string()` et le valide
 * ici contre `process.env.INTERNAL_API_KEY`. Lève une `ConvexError` typée si
 * la clé manque ou diverge.
 *
 * Parité dev : si `INTERNAL_API_KEY` n'est pas configurée côté déploiement, on
 * laisse passer (même comportement que le bridge Node et la dépendance FastAPI
 * `verify_internal_key`). En prod, la clé DOIT être posée des deux côtés.
 */
export function assertInternalKey(provided: string): void {
  const expected = process.env.INTERNAL_API_KEY;
  if (!expected) return; // mode dev : clé non configurée -> on laisse passer
  if (provided !== expected) {
    throw new ConvexError({
      code: "UNAUTHORIZED",
      message: "Clé interne invalide ou manquante",
    });
  }
}
