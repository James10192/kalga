import { defineApp } from "convex/server";
// Import depuis le composant LOCAL, PAS depuis "@convex-dev/better-auth/convex.config".
import betterAuth from "./betterAuth/convex.config";

const app = defineApp();
app.use(betterAuth);

export default app;
