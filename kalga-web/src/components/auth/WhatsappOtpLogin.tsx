import * as React from "react"
import { Loader2, MessageCircle } from "lucide-react"
import { authClient } from "@/lib/auth-client"
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp"
import { AuthError } from "./AuthFeedback"
import {
  formatDisplayPhone,
  isValidLocalPhone,
  toCanonicalPhone,
} from "./phone"

interface WhatsappOtpLoginProps {
  /** Partie locale du numero saisi en haut du formulaire (sans indicatif). */
  localPhone: string
}

/**
 * Connexion par code WhatsApp (OTP) — chemin secondaire de /login.
 * Le marchand recoit un code sur SA propre session WhatsApp (pas de numero
 * central KALGA). Reutilise le numero deja saisi dans le formulaire principal.
 */
export function WhatsappOtpLogin({ localPhone }: WhatsappOtpLoginProps) {
  const [step, setStep] = React.useState<"idle" | "code">("idle")
  const [code, setCode] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(false)

  const canonical = toCanonicalPhone(localPhone)

  async function sendCode() {
    setError(null)
    if (!isValidLocalPhone(localPhone)) {
      setError("Entrez d'abord un numero WhatsApp valide ci-dessus.")
      return
    }
    setLoading(true)
    try {
      const { error: sendError } = await authClient.phoneNumber.sendOtp({
        phoneNumber: canonical,
      })
      if (sendError) {
        setError(
          sendError.message ?? "Envoi du code impossible. Reessayez.",
        )
        setLoading(false)
        return
      }
      setStep("code")
    } catch {
      setError("Service indisponible. Reessayez dans un instant.")
    } finally {
      setLoading(false)
    }
  }

  async function verifyCode() {
    setError(null)
    if (code.length < 6) {
      setError("Entrez le code a 6 chiffres recu sur WhatsApp.")
      return
    }
    setLoading(true)
    try {
      const { error: verifyError } = await authClient.phoneNumber.verify({
        phoneNumber: canonical,
        code,
      })
      if (verifyError) {
        setError(verifyError.message ?? "Code incorrect ou expire.")
        setLoading(false)
        return
      }
      // Restaure l'organisation active (sinon withOrg -> "No active organization").
      try {
        const orgs = await authClient.organization.list()
        const first = orgs?.data?.[0]
        if (first) {
          await authClient.organization.setActive({ organizationId: first.id })
        }
      } catch {
        /* non bloquant */
      }
      window.location.href = "/app"
    } catch {
      setError("La verification a echoue. Reessayez.")
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line bg-page p-4">
      {error ? <AuthError>{error}</AuthError> : null}

      {step === "idle" ? (
        <>
          <p className="flex items-center gap-2 text-sm text-ink-muted">
            <MessageCircle className="size-4 text-primary" />
            Recevez un code sur WhatsApp pour vous connecter sans mot de passe.
          </p>
          <button
            type="button"
            onClick={sendCode}
            disabled={loading}
            className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-line bg-surface text-sm font-medium text-ink shadow-soft transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Envoi du code...
              </>
            ) : (
              "Recevoir un code WhatsApp"
            )}
          </button>
        </>
      ) : (
        <>
          <p className="text-sm text-ink-muted">
            Code envoye sur WhatsApp au{" "}
            <span className="tabular font-medium text-ink">
              {formatDisplayPhone(canonical)}
            </span>
            .
          </p>
          <div className="flex justify-center py-1">
            <InputOTP
              maxLength={6}
              value={code}
              onChange={setCode}
              disabled={loading}
            >
              <InputOTPGroup className="gap-2">
                {[0, 1, 2, 3, 4, 5].map((i) => (
                  <InputOTPSlot
                    key={i}
                    index={i}
                    className="size-11 rounded-md border-line font-mono text-lg first:rounded-md last:rounded-md"
                  />
                ))}
              </InputOTPGroup>
            </InputOTP>
          </div>
          <button
            type="button"
            onClick={verifyCode}
            disabled={loading}
            className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary text-sm font-medium text-white transition-colors hover:bg-primary-deep disabled:pointer-events-none disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Verification...
              </>
            ) : (
              "Se connecter"
            )}
          </button>
          <button
            type="button"
            onClick={() => {
              setStep("idle")
              setCode("")
              setError(null)
            }}
            className="text-center text-xs font-medium text-ink-muted hover:text-ink"
          >
            Renvoyer un code
          </button>
        </>
      )}
    </div>
  )
}
