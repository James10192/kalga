import { createFileRoute } from "@tanstack/react-router";
import { fetchAuthQuery } from "~/lib/auth-server";
import { api } from "../../../convex/_generated/api";

// Proxy serveur TanStack -> bridge WhatsApp (kalga-whatsapp, port 3001).
// Garde le port du bridge INTERNE : le client ne parle jamais au bridge.
//
// Securite (plan 010 B) :
//  - exige une session authentifiee (resolue via fetchAuthQuery + cookie),
//  - force le `phone` = celui du marchand courant (resolu serveur via
//    merchants.currentMerchant) : jamais un numero arbitraire du client,
//  - rate-limit best-effort par IP+phone,
//  - erreurs JSON claires (401 / 503 / 429).
//
// IMPORTANT : exporter `Route`, sinon le router-plugin ignore le fichier.

const BRIDGE_URL = () => process.env.KALGA_WHATSAPP_URL || "http://localhost:3001";
const INTERNAL_KEY = () => process.env.INTERNAL_API_KEY || "";

/** Sous-chemins exposes par le proxy (mappes vers le bridge). */
type SubPath = "connect" | "pairing" | "status" | "qr";

function jsonError(status: number, message: string): Response {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Extrait le dernier segment significatif apres /api/wa/. */
function subPathFromUrl(url: string): string {
  const { pathname } = new URL(url);
  const after = pathname.replace(/^\/api\/wa\/?/, "");
  return after.split("/")[0] ?? "";
}

/** Headers forwardes au bridge (la cle interne est requise sur POST). */
function bridgeHeaders(extra?: Record<string, string>): Record<string, string> {
  const key = INTERNAL_KEY();
  return {
    ...(key ? { "X-Internal-Key": key } : {}),
    ...extra,
  };
}

// --- Rate limit best-effort (memoire process, fenetre glissante) -----------
// Suffisant pour amortir le polling/abus ; pas une defense forte (process-local).
const RL_WINDOW_MS = 10_000;
const RL_MAX = 25; // 25 requetes / 10s par (IP + phone)
const rlBuckets = new Map<string, number[]>();

function rateLimited(ip: string, phone: string): boolean {
  const k = `${ip}:${phone}`;
  const now = Date.now();
  const hits = (rlBuckets.get(k) ?? []).filter((t) => now - t < RL_WINDOW_MS);
  hits.push(now);
  rlBuckets.set(k, hits);
  return hits.length > RL_MAX;
}

function clientIp(request: Request): string {
  const xff = request.headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0]!.trim();
  return request.headers.get("x-real-ip") ?? "unknown";
}

/**
 * Resout le marchand courant via la session (cookie) et renvoie son numero.
 * `fetchAuthQuery` lit le cookie de session automatiquement (contexte serveur).
 */
async function resolveMerchantPhone(): Promise<
  { ok: true; phone: string } | { ok: false; status: number; message: string }
> {
  let merchant: { phone?: string } | null = null;
  try {
    merchant = (await fetchAuthQuery(api.merchants.currentMerchant, {})) as
      | { phone?: string }
      | null;
  } catch {
    return { ok: false, status: 401, message: "Session requise" };
  }
  if (!merchant) {
    return { ok: false, status: 401, message: "Session requise" };
  }
  const phone = String(merchant.phone ?? "").replace(/[^\d]/g, "");
  if (!phone) {
    return { ok: false, status: 409, message: "Aucun numero marchand lie" };
  }
  return { ok: true, phone };
}

/** Forward GET vers le bridge en propageant statut + body (JSON ou binaire). */
async function forwardGet(path: string): Promise<Response> {
  let upstream: Response;
  try {
    upstream = await fetch(`${BRIDGE_URL()}${path}`, {
      method: "GET",
      headers: bridgeHeaders(),
    });
  } catch {
    return jsonError(503, "Service WhatsApp indisponible, reessayez");
  }
  const contentType = upstream.headers.get("content-type") ?? "application/json";
  const headers: Record<string, string> = {
    "Content-Type": contentType,
    "Cache-Control": "no-store",
  };
  const body = await upstream.arrayBuffer();
  return new Response(body, { status: upstream.status, headers });
}

/** Forward POST JSON vers le bridge. */
async function forwardPost(path: string, payload: unknown): Promise<Response> {
  let upstream: Response;
  try {
    upstream = await fetch(`${BRIDGE_URL()}${path}`, {
      method: "POST",
      headers: bridgeHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
  } catch {
    return jsonError(503, "Service WhatsApp indisponible, reessayez");
  }
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

/** Pipeline commun : auth -> rate-limit -> dispatch sous-chemin. */
async function handle(request: Request, method: "GET" | "POST"): Promise<Response> {
  const sub = subPathFromUrl(request.url) as SubPath | "";

  const resolved = await resolveMerchantPhone();
  if (!resolved.ok) return jsonError(resolved.status, resolved.message);
  const phone = resolved.phone;

  if (rateLimited(clientIp(request), phone)) {
    return jsonError(429, "Trop de tentatives, patientez quelques instants");
  }

  if (method === "POST") {
    if (sub !== "connect") return jsonError(404, "Route inconnue");
    // Le phone vient TOUJOURS de la session, jamais du body client.
    return forwardPost("/connect", { merchant_phone: phone });
  }

  // GET : pairing | status | qr (phone force par la session)
  switch (sub) {
    case "pairing":
      return forwardGet(`/pairing-code/${phone}`);
    case "status":
      return forwardGet(`/status/${phone}`);
    case "qr":
      return forwardGet(`/qr-image/${phone}`);
    default:
      return jsonError(404, "Route inconnue");
  }
}

export const Route = createFileRoute("/api/wa/$")({
  server: {
    handlers: {
      GET: ({ request }) => handle(request, "GET"),
      POST: ({ request }) => handle(request, "POST"),
    },
  },
});
