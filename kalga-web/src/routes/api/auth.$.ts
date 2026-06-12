import { createFileRoute } from "@tanstack/react-router";
import { handler } from "~/lib/auth-server";

// Proxy /api/auth/* -> handler serveur Better Auth (vers le deploiement Convex).
// IMPORTANT : exporter `Route`, sinon le router-plugin ignore le fichier.
export const Route = createFileRoute("/api/auth/$")({
  server: {
    handlers: {
      GET: ({ request }) => handler(request),
      POST: ({ request }) => handler(request),
    },
  },
});
