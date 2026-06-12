import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { useQuery, useMutation } from "convex/react"
import { Check, Copy, KeyRound, TicketPlus } from "lucide-react"
import { api } from "../../../../convex/_generated/api"
import { Button } from "@/components/ui/button"

/**
 * Admin — émission de CODES D'ACTIVATION.
 * Formulaire : sélection marchand + durée + bouton "Générer un code". Appelle
 * api.admin.issueActivationCode (mutation gardée admin) puis affiche le code.
 * États : chargement options, vide, succès (code copiable), erreur.
 */
export const Route = createFileRoute("/app/admin/codes")({
  component: AdminCodesPage,
})

type Option = { id: string; name: string; slug: string }

function AdminCodesPage() {
  const options = useQuery(api.admin.listMerchantOptions, {}) as
    | Option[]
    | undefined
  const issue = useMutation(api.admin.issueActivationCode)

  const [merchantId, setMerchantId] = useState("")
  const [days, setDays] = useState(30)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<
    { code: string; expiresAt: number; merchantName: string } | null
  >(null)
  const [copied, setCopied] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setCopied(false)
    if (!merchantId) {
      setError("Sélectionnez un marchand.")
      return
    }
    setPending(true)
    try {
      const res = await issue({
        merchantId: merchantId as never,
        expiresInDays: days,
      })
      const merchantName =
        options?.find((o) => o.id === merchantId)?.name ?? "Marchand"
      setResult({ ...res, merchantName })
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Échec de l'émission du code, réessayez.",
      )
    } finally {
      setPending(false)
    }
  }

  async function copyCode() {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result.code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard indisponible : silencieux */
    }
  }

  return (
    <div className="max-w-[640px] space-y-5">
      <div>
        <h1 className="font-display text-[22px] font-bold tracking-tight">
          Codes d'activation
        </h1>
        <p className="mt-0.5 text-[13.5px] text-ink-muted">
          Générez un code d'abonnement pour un marchand. Le code reste en
          attente jusqu'à son activation par le marchand.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-2xl border border-line bg-surface p-5 shadow-soft"
      >
        <div className="space-y-1.5">
          <label
            htmlFor="merchant"
            className="text-[13px] font-medium text-ink"
          >
            Marchand
          </label>
          <select
            id="merchant"
            value={merchantId}
            onChange={(e) => setMerchantId(e.target.value)}
            disabled={options === undefined}
            className="h-12 w-full rounded-xl border border-line bg-surface px-3 text-[14.5px] text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60"
          >
            <option value="">
              {options === undefined
                ? "Chargement..."
                : "Sélectionner un marchand"}
            </option>
            {options?.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name} ({o.slug})
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="days" className="text-[13px] font-medium text-ink">
            Validité (jours)
          </label>
          <div className="flex items-center gap-2">
            {[30, 90, 365].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays(d)}
                className={
                  "h-12 flex-1 rounded-xl border text-[14px] font-medium transition-colors " +
                  (days === d
                    ? "border-primary bg-primary-tint text-primary-deep"
                    : "border-line bg-surface text-ink-muted hover:bg-secondary/60")
                }
              >
                {d} j
              </button>
            ))}
          </div>
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-xl bg-danger-tint px-3 py-2 text-[13px] font-medium text-danger"
          >
            {error}
          </p>
        )}

        <Button
          type="submit"
          size="lg"
          disabled={pending || options === undefined}
          className="h-12 w-full rounded-xl text-[15px]"
        >
          {pending ? (
            "Génération..."
          ) : (
            <>
              <TicketPlus className="h-4 w-4" /> Générer un code
            </>
          )}
        </Button>
      </form>

      {result && (
        <div className="rounded-2xl border border-primary/30 bg-primary-tint p-5">
          <div className="flex items-center gap-2 text-primary-deep">
            <KeyRound className="h-4 w-4" />
            <p className="text-[13px] font-semibold">
              Code généré pour {result.merchantName}
            </p>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <code className="flex-1 rounded-xl border border-primary/20 bg-surface px-4 py-3 font-mono text-[22px] font-bold tracking-[0.2em] text-ink">
              {result.code}
            </code>
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={copyCode}
              className="h-12 rounded-xl border-primary/30"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-primary-deep" /> Copié
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" /> Copier
                </>
              )}
            </Button>
          </div>
          <p className="mt-3 text-[12.5px] text-primary-deep/80">
            Expire le{" "}
            {new Intl.DateTimeFormat("fr-FR", {
              day: "numeric",
              month: "long",
              year: "numeric",
            }).format(new Date(result.expiresAt))}
            . Transmettez ce code au marchand (paiement Wave ou Orange Money hors
            application).
          </p>
        </div>
      )}
    </div>
  )
}
