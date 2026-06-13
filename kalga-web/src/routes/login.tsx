import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { useState } from "react"
import { ChevronDown, Loader2, MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { authClient } from "@/lib/auth-client"
import {
  AuthShell,
  AuthError,
  FieldLabel,
  PhoneInput,
  PasswordInput,
} from "@/components/auth"
import { WhatsappOtpLogin } from "@/components/auth/WhatsappOtpLogin"
import {
  isValidLocalPhone,
  phoneToEmail,
  toCanonicalPhone,
} from "@/components/auth/phone"

/**
 * /login — connexion marchand (page publique).
 *
 * Chemin PRINCIPAL : numero + mot de passe (fiable, plan 010 E).
 *  `authClient.signIn.email({ email: `${digits}@kalga.local`, password })`
 *  -> succes -> `window.location.href = "/app"` (reload pour propager le JWT).
 *
 * Chemin SECONDAIRE repliable : connexion par code WhatsApp (OTP), via la
 * propre session WhatsApp du marchand (aucun numero central KALGA).
 */
export const Route = createFileRoute("/login")({
  beforeLoad: ({ context }) => {
    if (context.isAuthenticated) throw redirect({ to: "/app" })
  },
  head: () => ({
    meta: [{ title: "Connexion · KALGA" }],
  }),
  component: LoginPage,
})

function LoginPage() {
  const [phone, setPhone] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [otpOpen, setOtpOpen] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!isValidLocalPhone(phone)) {
      setError("Entrez un numero WhatsApp valide.")
      return
    }
    if (!password) {
      setError("Entrez votre mot de passe.")
      return
    }

    const digits = toCanonicalPhone(phone)
    setLoading(true)
    try {
      const { error: signInError } = await authClient.signIn.email({
        email: phoneToEmail(digits),
        password,
      })
      if (signInError) {
        setError(
          "Numero ou mot de passe incorrect. Verifiez vos identifiants.",
        )
        setLoading(false)
        return
      }
      // Une nouvelle session n'a pas d'organisation active : on la restaure
      // (sinon withOrg -> "No active organization" au chargement du dashboard).
      try {
        const orgs = await authClient.organization.list()
        const first = orgs?.data?.[0]
        if (first) {
          await authClient.organization.setActive({ organizationId: first.id })
        }
      } catch {
        // non bloquant : la gate /app gerera l'absence d'organisation
      }
      window.location.href = "/app"
    } catch {
      setError("Service indisponible. Reessayez dans un instant.")
      setLoading(false)
    }
  }

  return (
    <AuthShell
      rail="login"
      title="Bon retour"
      subtitle="Connectez-vous pour retrouver vos conversations et vos ventes."
      footer={
        <>
          Pas encore de compte ?{" "}
          <Link
            to="/signup"
            className="font-medium text-primary-deep hover:underline"
          >
            Creer un compte
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error ? <AuthError>{error}</AuthError> : null}

        <div>
          <FieldLabel htmlFor="login-phone">Numero WhatsApp</FieldLabel>
          <PhoneInput
            id="login-phone"
            value={phone}
            onChange={setPhone}
            disabled={loading}
            autoFocus
            hint={undefined}
          />
        </div>

        <div>
          <FieldLabel htmlFor="login-password">Mot de passe</FieldLabel>
          <PasswordInput
            id="login-password"
            value={password}
            onChange={setPassword}
            disabled={loading}
            autoComplete="current-password"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-1 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary text-base font-medium text-white shadow-soft transition-colors hover:bg-primary-deep disabled:pointer-events-none disabled:opacity-60"
        >
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Connexion...
            </>
          ) : (
            "Se connecter"
          )}
        </button>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs text-ink-faint">
        <span className="h-px flex-1 bg-line" />
        ou
        <span className="h-px flex-1 bg-line" />
      </div>

      <button
        type="button"
        onClick={() => setOtpOpen((o) => !o)}
        aria-expanded={otpOpen}
        className="inline-flex h-11 w-full items-center justify-between rounded-xl border border-line bg-surface px-4 text-sm font-medium text-ink shadow-soft transition-colors hover:bg-muted"
      >
        <span className="inline-flex items-center gap-2">
          <MessageCircle className="size-4 text-primary" />
          Connexion par code WhatsApp
        </span>
        <ChevronDown
          className={cn(
            "size-4 text-ink-faint transition-transform",
            otpOpen && "rotate-180",
          )}
        />
      </button>

      {otpOpen ? (
        <div className="mt-3">
          <WhatsappOtpLogin localPhone={phone} />
        </div>
      ) : null}
    </AuthShell>
  )
}
