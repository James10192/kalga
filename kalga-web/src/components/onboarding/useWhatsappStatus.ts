import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Hook de connexion/polling WhatsApp (plan 010 §E).
 *
 * Source : le proxy serveur `/api/wa/*` (le client ne parle jamais au bridge
 * 3001). Le proxy force le `phone` = marchand courant via la session.
 *
 * Contrainte Baileys (doc) : sur une MEME socket, code d'appairage et QR sont
 * MUTUELLEMENT EXCLUSIFs (demander le code supprime l'emission du QR). Pour
 * supporter les deux onglets, on (re)connecte la socket DANS LE MODE choisi :
 *  - `setMethod('qr')`  -> connect sans demander de code  -> le bridge emet un QR
 *  - `setMethod('code')`-> connect + requestPairingCode    -> le bridge donne le code
 * Le bridge revoque/recree la socket quand le mode change (cf. `/connect?method=`).
 *
 * Ensuite : GET /status toutes les ~2.5s jusqu'a `ready`. A `ready`, on stoppe et
 * on expose `realPhone` pour la mutation Convex `linkWhatsapp`.
 */

export type WaMethod = "qr" | "code"

export type WaPhase =
  | "idle"
  | "connecting" // (re)connexion dans le mode demande
  | "waiting" // code/QR dispo, en attente du lien
  | "linking" // intermediaire (connected mais pas ready)
  | "ready" // session liee
  | "error"

export type WaError =
  | null
  | "rate_limited"
  | "service_down"
  | "expired"
  | "unknown"

export interface WhatsappStatus {
  phase: WaPhase
  pairingCode: string | null
  realPhone: string | null
  qrAvailable: boolean
  error: WaError
  /** Relance la connexion dans le mode courant (« Generer un nouveau code »). */
  refresh: () => void
  /** (Re)connecte dans le mode choisi. A appeler au montage et au switch d'onglet. */
  setMethod: (method: WaMethod) => void
}

const POLL_INTERVAL_MS = 2500
const PAIRING_RETRY_MS = 1500
const PAIRING_MAX_TRIES = 8

interface BridgeStatus {
  connected?: boolean
  ready?: boolean
  qrCode?: string | null
  realPhone?: string | null
  pairingCode?: string | null
}

function errorFromStatus(httpStatus: number): WaError {
  if (httpStatus === 429) return "rate_limited"
  if (httpStatus === 503) return "service_down"
  if (httpStatus === 404 || httpStatus === 409) return "expired"
  return "unknown"
}

export function useWhatsappStatus(): WhatsappStatus {
  const [phase, setPhase] = useState<WaPhase>("idle")
  const [pairingCode, setPairingCode] = useState<string | null>(null)
  const [realPhone, setRealPhone] = useState<string | null>(null)
  const [qrAvailable, setQrAvailable] = useState(false)
  const [error, setError] = useState<WaError>(null)

  const aliveRef = useRef(true)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cycleRef = useRef(0)
  const methodRef = useRef<WaMethod>("qr")

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const poll = useCallback(async (cycle: number) => {
    if (!aliveRef.current || cycle !== cycleRef.current) return
    try {
      const res = await fetch("/api/wa/status", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "include",
      })
      if (!aliveRef.current || cycle !== cycleRef.current) return

      if (!res.ok) {
        if (res.status === 404) {
          timerRef.current = setTimeout(() => poll(cycle), POLL_INTERVAL_MS)
          return
        }
        setError(errorFromStatus(res.status))
        setPhase("error")
        if (res.status === 429) {
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
        return
      }

      setPhase(data.connected ? "linking" : "waiting")
      setError(null)
      timerRef.current = setTimeout(() => poll(cycle), POLL_INTERVAL_MS)
    } catch {
      if (!aliveRef.current || cycle !== cycleRef.current) return
      setError("service_down")
      setPhase("error")
      timerRef.current = setTimeout(() => poll(cycle), POLL_INTERVAL_MS * 2)
    }
  }, [])

  // En mode 'code', le code peut etre `pending` (socket pas prete) : on retente
  // GET /pairing jusqu'a l'obtenir.
  const fetchPairing = useCallback(async (cycle: number, tries: number) => {
    if (!aliveRef.current || cycle !== cycleRef.current) return
    try {
      const res = await fetch("/api/wa/pairing", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "include",
      })
      if (!aliveRef.current || cycle !== cycleRef.current) return
      if (res.ok) {
        const p = (await res.json()) as { pairingCode?: string | null }
        if (p.pairingCode) {
          setPairingCode(p.pairingCode)
          return
        }
        if (tries < PAIRING_MAX_TRIES) {
          setTimeout(() => fetchPairing(cycle, tries + 1), PAIRING_RETRY_MS)
        }
        return
      }
      if (res.status === 429) {
        setError("rate_limited")
        return
      }
      if (res.status === 409) return // deja lie
      if (tries < PAIRING_MAX_TRIES) {
        setTimeout(() => fetchPairing(cycle, tries + 1), PAIRING_RETRY_MS * 1.4)
      }
    } catch {
      if (tries < PAIRING_MAX_TRIES) {
        setTimeout(() => fetchPairing(cycle, tries + 1), PAIRING_RETRY_MS * 1.4)
      }
    }
  }, [])

  const setMethod = useCallback(
    (method: WaMethod) => {
      methodRef.current = method
      clearTimer()
      cycleRef.current += 1
      const cycle = cycleRef.current
      setPhase("connecting")
      setError(null)
      setPairingCode(null)
      setQrAvailable(false)

      void (async () => {
        try {
          // (Re)connecte la socket DANS le mode demande (le bridge revoque
          // l'ancienne socket si le mode change).
          const res = await fetch(`/api/wa/connect?method=${method}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
          })
          if (!aliveRef.current || cycle !== cycleRef.current) return
          if (!res.ok) {
            setError(errorFromStatus(res.status))
            setPhase("error")
            return
          }
          setPhase("waiting")
          if (method === "code") void fetchPairing(cycle, 0)
          void poll(cycle)
        } catch {
          if (!aliveRef.current || cycle !== cycleRef.current) return
          setError("service_down")
          setPhase("error")
        }
      })()
    },
    [clearTimer, poll, fetchPairing],
  )

  useEffect(() => {
    aliveRef.current = true
    return () => {
      aliveRef.current = false
      clearTimer()
    }
  }, [clearTimer])

  const refresh = useCallback(() => {
    setMethod(methodRef.current)
  }, [setMethod])

  return { phase, pairingCode, realPhone, qrAvailable, error, refresh, setMethod }
}
