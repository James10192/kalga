import { useEffect, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import { useMutation } from "convex/react"
import gsap from "gsap"
import { ExternalLink, CircleCheckBig } from "lucide-react"
import { api } from "../../../convex/_generated/api"
import { Button } from "@/components/ui/button"
import { useWhatsappStatus } from "./useWhatsappStatus"
import {
  Header,
  SegmentedToggle,
  CodePanel,
  QrPanel,
  StatusRow,
  type TabKey,
} from "./ConnectPanels"

/**
 * Onglet par defaut = CODE partout. Contrainte Baileys (confirmee doc) : un code
 * d'appairage et un QR sont MUTUELLEMENT EXCLUSIFs sur une meme socket (demander
 * le code supprime l'emission du QR). Le code est universel (meme telephone, ou
 * lu sur desktop puis saisi dans WhatsApp) -> on le met en avant ; le QR reste un
 * repli secondaire.
 */
function useDefaultTab(): TabKey {
  return "code"
}

export function WhatsAppConnect() {
  const defaultTab = useDefaultTab()
  const [tab, setTab] = useState<TabKey>(defaultTab)
  // Synchronise l'onglet par defaut une fois la media query resolue (client).
  useEffect(() => setTab(defaultTab), [defaultTab])

  const { phase, pairingCode, realPhone, qrAvailable, error, refresh } =
    useWhatsappStatus(true)
  const linkWhatsapp = useMutation(api.merchants.linkWhatsapp)
  const linkedRef = useRef(false)
  const [toast, setToast] = useState<string | null>(null)

  // Au passage `ready` : on pose le lien Convex une seule fois (idempotent cote
  // serveur, mais on evite les mutations en boucle).
  useEffect(() => {
    if (phase !== "ready" || linkedRef.current) return
    linkedRef.current = true
    void linkWhatsapp({ realPhone: realPhone ?? "" })
  }, [phase, realPhone, linkWhatsapp])

  // Toast auto-dismiss.
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 1800)
    return () => clearTimeout(t)
  }, [toast])

  if (phase === "ready") return <SuccessState />

  return (
    <div className="px-4 pt-6 pb-10">
      <Header />
      <SegmentedToggle tab={tab} onChange={setTab} />

      {tab === "code" ? (
        <CodePanel
          code={pairingCode}
          error={error}
          phase={phase}
          onCopy={(c) => {
            void navigator.clipboard?.writeText(c).then(() => setToast("Code copie"))
          }}
          onRefresh={refresh}
        />
      ) : (
        <QrPanel available={qrAvailable} error={error} onRefresh={refresh} />
      )}

      <StatusRow phase={phase} />

      <a
        href="whatsapp://"
        className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-line bg-surface px-5 text-sm font-medium text-ink hover:bg-muted"
        style={{ height: 44 }}
      >
        <ExternalLink className="size-4" />
        Ouvrir WhatsApp
      </a>

      {toast && (
        <div className="pointer-events-none fixed inset-x-0 bottom-28 z-50 flex justify-center">
          <span className="rounded-full bg-ink px-4 py-2 text-xs font-medium text-white shadow-md">
            {toast}
          </span>
        </div>
      )}
    </div>
  )
}

function SuccessState() {
  const scope = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (typeof window === "undefined") return
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    if (reduce || !scope.current) return
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".wa-check",
        { scale: 0.6, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.7)" },
      )
    }, scope)
    return () => ctx.revert()
  }, [])

  return (
    <div ref={scope} className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <span className="wa-check flex size-20 items-center justify-center rounded-full bg-primary-tint text-primary-deep">
        <CircleCheckBig className="size-10" />
      </span>
      <h1 className="mt-5 font-display text-2xl font-semibold tracking-tight text-ink">
        Votre boutique est prete
      </h1>
      <p className="mt-1 text-sm text-ink-muted">
        Votre WhatsApp est connecte. Le bot est en ligne.
      </p>
      <Button asChild size="lg" className="mt-7 h-11 px-6">
        <Link to="/app">Aller au tableau de bord</Link>
      </Button>
    </div>
  )
}
