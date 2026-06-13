import { useEffect, useMemo, useRef, useState } from "react"
import gsap from "gsap"
import QRCode from "qrcode"
import {
  Smartphone,
  QrCode,
  Copy,
  Check,
  Loader2,
  RefreshCw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { WaPhase, WaError } from "./useWhatsappStatus"

/** Onglet de methode de liaison (code d'appairage ou QR). */
export type TabKey = "code" | "qr"

const STEPS = [
  "Ouvrez WhatsApp sur ce telephone",
  "Allez dans Reglages, puis Appareils connectes",
  "Touchez Connecter un appareil, puis Lier avec un numero",
  "Entrez ce code",
] as const

/** Statut lisible derive de la phase de poll. */
function statusLabel(phase: WaPhase): { text: string; tone: "wait" | "go" | "ok" } {
  if (phase === "ready") return { text: "Connecte", tone: "ok" }
  if (phase === "linking") return { text: "Connexion en cours...", tone: "go" }
  return { text: "En attente de connexion...", tone: "wait" }
}

function errorMessage(error: WaError): string {
  switch (error) {
    case "rate_limited":
      return "Trop de tentatives, patientez quelques instants."
    case "service_down":
      return "Service indisponible, reessayez."
    case "expired":
      return "Le code a expire. Generez-en un nouveau."
    default:
      return "Une erreur est survenue, reessayez."
  }
}

export function Header() {
  return (
    <header className="mb-5">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
        Connecter WhatsApp
      </h1>
      <p className="mt-1 text-sm text-ink-muted">
        Liez votre WhatsApp pour que le bot reponde et vende a votre place.
      </p>
    </header>
  )
}

export function SegmentedToggle({
  tab,
  onChange,
}: {
  tab: TabKey
  onChange: (t: TabKey) => void
}) {
  return (
    <div className="mb-5 inline-flex w-full rounded-lg bg-muted p-[3px]">
      {(["code", "qr"] as const).map((key) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          className={cn(
            "flex h-9 flex-1 items-center justify-center gap-1.5 rounded-md text-sm font-medium transition-colors",
            tab === key
              ? "bg-surface text-ink shadow-xs"
              : "text-ink-muted hover:text-ink",
          )}
        >
          {key === "code" ? <Smartphone className="size-4" /> : <QrCode className="size-4" />}
          {key === "code" ? "Code" : "QR"}
        </button>
      ))}
    </div>
  )
}

function CodeCells({ code, onCopy }: { code: string; onCopy: (c: string) => void }) {
  const chars = useMemo(() => code.replace(/[^A-Za-z0-9]/g, "").slice(0, 8).split(""), [code])
  const scope = useRef<HTMLButtonElement>(null)

  // Apparition en stagger (GSAP via gsap.context, jamais @gsap/react).
  useEffect(() => {
    if (typeof window === "undefined") return
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    if (reduce || !scope.current) return
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".wa-cell",
        { y: 8, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.32, stagger: 0.04, ease: "power2.out" },
      )
    }, scope)
    return () => ctx.revert()
  }, [code])

  return (
    <button
      ref={scope}
      type="button"
      onClick={() => onCopy(code)}
      aria-label="Copier le code d'appairage"
      className="group flex w-full items-center justify-center gap-1.5"
    >
      {chars.map((ch, i) => (
        <span key={i} className="contents">
          <span className="wa-cell flex h-14 w-9 items-center justify-center rounded-lg border border-line bg-surface font-mono text-3xl font-semibold text-ink sm:w-11">
            {ch.toUpperCase()}
          </span>
          {i === 3 && <span className="px-0.5 text-2xl text-ink-faint">-</span>}
        </span>
      ))}
    </button>
  )
}

export function CodePanel({
  code,
  error,
  phase,
  onCopy,
  onRefresh,
}: {
  code: string | null
  error: WaError
  phase: WaPhase
  onCopy: (c: string) => void
  onRefresh: () => void
}) {
  return (
    <section className="rounded-2xl border border-line bg-page/40 p-4">
      {code ? (
        <>
          <CodeCells code={code} onCopy={onCopy} />
          <button
            type="button"
            onClick={() => onCopy(code)}
            className="mx-auto mt-3 flex items-center gap-1.5 text-xs font-medium text-ink-muted hover:text-ink"
          >
            <Copy className="size-3.5" />
            Toucher pour copier
          </button>
        </>
      ) : error ? (
        <ErrorBlock message={errorMessage(error)} onRetry={onRefresh} retryable={error !== "rate_limited"} />
      ) : (
        <div className="flex h-14 items-center justify-center gap-2 text-sm text-ink-muted">
          <Loader2 className="size-4 animate-spin" />
          Generation du code...
        </div>
      )}

      <ol className="mt-5 space-y-3">
        {STEPS.map((step, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary-tint text-[13px] font-semibold text-primary-deep">
              {i + 1}
            </span>
            <span className="pt-0.5 text-sm text-ink">{step}</span>
          </li>
        ))}
      </ol>

      {phase !== "connecting" && (
        <button
          type="button"
          onClick={onRefresh}
          className="mt-4 flex items-center gap-1.5 text-xs font-medium text-ink-muted hover:text-ink"
        >
          <RefreshCw className="size-3.5" />
          Generer un nouveau code
        </button>
      )}
    </section>
  )
}

/**
 * Rend le QR DEPUIS la chaine `qrCode` du status (cote client, via la lib
 * `qrcode`). On NE depend PLUS de l'endpoint image `/api/wa/qr` (qui pouvait
 * 404 sur une course quand le bridge n'avait pas encore le QR) : la chaine vient
 * avec le poll de status, toujours coherente.
 */
function QrImage({ value }: { value: string }) {
  const [src, setSrc] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    void QRCode.toDataURL(value, { width: 224, margin: 2 })
      .then((url) => {
        if (alive) setSrc(url)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [value])

  if (!src) {
    return (
      <div className="flex h-56 items-center justify-center gap-2 text-sm text-ink-muted">
        <Loader2 className="size-4 animate-spin" />
        Generation du QR...
      </div>
    )
  }
  return (
    <img
      src={src}
      alt="QR code d'appairage WhatsApp"
      width={224}
      height={224}
      className="size-56 rounded-xl border border-line bg-white p-2"
    />
  )
}

export function QrPanel({
  qrCode,
  error,
  onRefresh,
}: {
  qrCode: string | null
  error: WaError
  onRefresh: () => void
}) {
  return (
    <section className="rounded-2xl border border-line bg-page/40 p-4">
      {error && error !== "expired" ? (
        <ErrorBlock message={errorMessage(error)} onRetry={onRefresh} retryable />
      ) : qrCode ? (
        <div className="flex flex-col items-center">
          <QrImage value={qrCode} />
        </div>
      ) : (
        <div className="flex h-56 items-center justify-center gap-2 text-sm text-ink-muted">
          <Loader2 className="size-4 animate-spin" />
          Generation du QR...
        </div>
      )}
      <p className="mt-3 text-center text-[13px] text-ink-muted">
        Scannez depuis un autre telephone ou un ordinateur.
      </p>
    </section>
  )
}

export function StatusRow({ phase }: { phase: WaPhase }) {
  const { text, tone } = statusLabel(phase)
  const dot =
    tone === "ok"
      ? "bg-primary"
      : tone === "go"
        ? "bg-livrer"
        : "bg-nego animate-pulse"
  const label = tone === "ok" ? "text-primary-deep" : "text-ink"
  return (
    <div className="mt-5 flex items-center gap-2">
      <span className={cn("size-2.5 rounded-full", dot)} />
      <span className={cn("text-sm font-medium", label)}>{text}</span>
      {tone === "ok" && <Check className="size-4 text-primary-deep" />}
    </div>
  )
}

function ErrorBlock({
  message,
  onRetry,
  retryable,
}: {
  message: string
  onRetry: () => void
  retryable: boolean
}) {
  return (
    <div className="rounded-lg border border-danger/20 bg-danger-tint px-3 py-3">
      <p className="text-sm text-danger">{message}</p>
      {retryable && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 flex items-center gap-1.5 text-xs font-medium text-danger hover:underline"
        >
          <RefreshCw className="size-3.5" />
          Reessayer
        </button>
      )}
    </div>
  )
}
