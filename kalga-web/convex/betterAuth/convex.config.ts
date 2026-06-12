import { defineComponent } from "convex/server";

// Composant Better Auth installé EN LOCAL (Local Install).
// Requis pour débloquer les plugins `organization` et `admin`, non supportés
// par le composant NPM par défaut (schéma figé).
const component = defineComponent("betterAuth");

export default component;
