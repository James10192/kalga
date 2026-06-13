import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Hook de polling du statut WhatsApp (plan 010 §E).
 *
 * Source de donnees : le proxy serveur `/api/wa/*` (le client ne parle jamais
 * au bridge port 3001). Le proxy force le `phone` = marchand courant via la
 * session ; aucun numero n'est envoye par le client.
 *
 * Cycle :
 *  - au montage : POST /api/wa/connect (initialise la socket Baileys) puis
 *    GET /api/wa/pairing pour recuperer le code d'appairage (8 caracteres).
 *  - ensuite : GET /api/wa/status toutes les ~2.5s, jusqu'a `ready`.
 *  - a `ready` : on stoppe le poll, on expose `realPhone` (numero reel remonte
 *    par le bridge) pour la mutation Convex `linkWhatsapp`.
 *
 * Gestion des etats limites : 429 (rate limit), 503 (bridge down), code expire.
 */

export type WaPhase =
  | "idle" // avant le 1er fetch
  | "connecting" // POST /connect en cours
  | "waiting" // code dispo, en attente du lien depuis WhatsApp
  | "linking" // statut intermediaire (qr/connected mais pas ready)
  | "ready" // session liee
  | "error" // erreur recuperable (voir `error`)

export type WaError =
  | null
  | "rate_limited" // 429
  | "service_down" // 503 / reseau
  | "expired" // code expire / introuvable
  | "unknown"

export interface WhatsappStatus {
  phase: WaPhase
  pairingCode: string | null
  realPhone: string | null
  qrAvailable: boolean
  error: WaError
  /** Relance un cycle complet (connect + pairing), pour « Generer un nouveau code ». */
  refresh: () => void
}

const POLL_INTERVAL_MS = 2500

interface BridgeStatus {
  connected?: boolean
  ready?: boolean
  qrCode?: string | null
  realPhone?: string | null
  pairingCode?: string | null
}

/** Map un code HTTP non-ok vers une erreur typee. */
function errorFromStatus(httpStatus: number): WaError {
  if (httpStatus === 429) return "rate_limited"
  if (httpStatus === 503) return "service_down"
  if (httpStatus === 404 || httpStatus === 409) return "expired"
  return "unknown"
}

export function useWhatsappStatus(enabled = true): WhatsappStatus {
  const [phase, setPhase] = useState<WaPhase>("idle")
  const [pairingCode, setPairingCode] = useState<string | null>(null)
  const [realPhone, setRealPhone] = useState<string | null>(null)
  const [qrAvailable, setQrAvailable] = useState(false)
  const [error, setError] = useState<WaError>(null)

  // Garde anti-poll-apres-unmount et anti-double-cycle.
  const aliveRef = useRef(true)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cycleRef = useRef(0)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const poll = useCallback(
    async (cycle: number) => {
      if (!aliveRef.current || cycle !== cycleRef.current) return
      try {
        const res = await fetch("/api/wa/status", {
          method: "GET",
          headers: { Accept: "application/json" },
          credentials: "include",
        })
        if (!aliveRef.current || cycle !== cycleRef.current) return

        if (!res.ok) {
          // 404 = pas encore de session : on retente (ce n'est pas fatal).
          if (res.status === 404) {
            timerRef.current = setTimeout(() => poll(cycle), POLL_INTERVAL_MS)
            return
          }
          setError(errorFromStatus(res.status))
          setPhase("error")
          if (res.status === 429) {
            // On retente plus lentement apres un rate limit.
            timerRef.current = setTimeout(() => poll(cycle), POLL_INTERVAL_MS * 3)
          }
          return
        }

        const data = (await res.json()) as BridgeStatus
        setQrAvailable(Boolean(data.qrCode))
        if (data.pairingCode) setPairingCode(data.pairingCode)

        if (data.ready) {
          setRealPhone(data.realPhone ?? null)
          setPhase("ready")
          setError(null)
          return // arret du poll
        }

        // Pas encore lie : on continue, en distinguant attente / connexion.
        setPhase(data.connected ? "linking" : "waiting")
        setError(null)
        timerRef.current = setTimeout(() => poll(cycle), POLL_INTERVAL_MS)
      } catch {
        if (!aliveRef.current || cycle !== cycleRef.current) return
        setError("service_down")
        setPhase("error")
        timerRef.current = setTimeout(() => poll(cycle), POLL_INTERVAL_MS * 2)
      }
    },
    [],
  )

  const start = useCallback(async () => {
    clearTimer()
    cycleRef.current += 1
    const cycle = cycleRef.current
    setPhase("connecting")
    setError(null)

    try {
      // 1. Initialise la socket cote bridge.
      const connectRes = await fetch("/api/wa/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      })
      if (!aliveRef.current || cycle !== cycleRef.current) return
      if (!connectRes.ok) {
        setError(errorFromStatus(connectRes.status))
        setPhase("error")
        return
      }

      // 2. Recupere le code d'appairage (peut etre `pending` au 1er appel).
      const pairingRes = await fetch("/api/wa/pairing", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "include",
      })
      if (!aliveRef.current || cycle !== cycleRef.current) return

      if (pairingRes.ok) {
        const pairing = (await pairingRes.json()) as { pairingCode?: string | null }
        if (pairing.pairingCode) setPairingCode(pairing.pairingCode)
      } else if (pairingRes.status === 409) {
        // Deja connecte : on laisse le poll constater `ready`.
      } else if (pairingRes.status === 429) {
        setError("rate_limited")
      } else if (pairingRes.status !== 202) {
        // 202 = pending (code en cours de generation) : non fatal, le poll suit.
        setError(errorFromStatus(pairingRes.status))
      }

      // 3. Demarre le poll de statut.
      setPhase("waiting")
      poll(cycle)
    } catch {
      if (!aliveRef.current || cycle !== cycleRef.current) return
      setError("service_down")
      setPhase("error")
    }
  }, [clearTimer, poll])

  useEffect(() => {
    aliveRef.current = true
    if (enabled) void start()
    return () => {
      aliveRef.current = false
      clearTimer()
    }
    // start est stable (deps stables) ; on relance uniquement si `enabled` bascule.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])

  const refresh = useCallback(() => {
    setPairingCode(null)
    setQrAvailable(false)
    void start()
  }, [start])

  return { phase, pairingCode, realPhone, qrAvailable, error, refresh }
}
