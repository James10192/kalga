/**
 * Garde-fou de démarrage — valide les variables d'env serveur obligatoires.
 * Référence : ARCHITECTURE_FRONTEND.md §7.1 (auth) + §7.4 (validation au boot).
 *
 * Sans ces variables, le proxy `/api/proxy/*` échoue en 500 cryptique à CHAQUE
 * requête (ex: « Empty password » quand NUXT_SESSION_PASSWORD est vide → tout le
 * frontend reste bloqué en chargement). On préfère échouer TÔT, une fois, avec
 * un message clair, plutôt que silencieusement à chaque appel.
 */

export default defineNitroPlugin(() => {
  const config = useRuntimeConfig()

  const missing: string[] = []

  if (!config.sessionPassword || config.sessionPassword.length < 32) {
    missing.push('NUXT_SESSION_PASSWORD (≥ 32 caractères — sinon le proxy plante en 500)')
  }
  if (!config.apiBackendUrl) {
    missing.push('NUXT_API_BACKEND_URL (URL du backend FastAPI, ex: http://localhost:8001)')
  }

  if (missing.length > 0) {
    const message =
      `[KALGA] Variables d'environnement serveur manquantes :\n` +
      missing.map((m) => `  - ${m}`).join('\n') +
      `\n→ Renseigne-les dans kalga-frontend/.env (voir .env.example).`
    // Loud + fail-fast : visible au démarrage, pas noyé dans un 500 par requête.
    console.error(message)
    throw new Error(message)
  }
})
