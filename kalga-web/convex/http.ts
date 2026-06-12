import { httpRouter } from "convex/server";
import { authComponent, createAuth } from "./auth";

const http = httpRouter();

// Monte /api/auth/* (GET/POST/OPTIONS). CORS obligatoire pour les frameworks
// client-side (TanStack Start). Plus de http.route manuel.
authComponent.registerRoutes(http, createAuth, { cors: true });

export default http;
