import { convexBetterAuthReactStart } from "@convex-dev/better-auth/react-start";

// Helpers SSR / serveur pour l'auth (handler des routes /api/auth/*, token SSR).
export const {
  handler,
  getToken,
  fetchAuthQuery,
  fetchAuthMutation,
  fetchAuthAction,
} = convexBetterAuthReactStart({
  convexUrl: process.env.VITE_CONVEX_URL!,
  convexSiteUrl: process.env.VITE_CONVEX_SITE_URL!, // .site, PAS .cloud
  // basePath: "/api/auth" (defaut)
});
