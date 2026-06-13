import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { useState } from "react"
import { useMutation } from "convex/react"
import { ArrowRight, Loader2, Store } from "lucide-react"
import { api } from "../../convex/_generated/api"
import { authClient } from "@/lib/auth-client"
import {
  AuthShell,
  AuthError,
  FieldLabel,
  PhoneInput,
  PasswordInput,
} from "@/components/auth"
import {
  isValidLocalPhone,
  phoneToEmail,
  toCanonicalPhone,
} from "@/components/auth/phone"
import { Input as TextInput } from "@/components/ui/input"

/**
 * /signup — creation de compte marchand (page publique).
 *
 * Flow (plan 010 E) :
 *  1. nom boutique + numero WhatsApp (+225) + mot de passe (>= 8).
 *  2. `authClient.signUp.email({ email: `${digits}@kalga.local`, password, name })`.
 *  3. si ok -> `provisionMerchantOrg({ name, phone: digits })`.
 *  4. `window.location.href = "/app"` (reload pour propager le JWT a Convex).
 *
 * Aucune organisation active n'est requise pour rendre cette page.
 */
export const Route = createFileRoute("/signup")({
  beforeLoad: ({ context }) => {
    if (context.isAuthenticated) throw redirect({ to: "/app" })
  },
  head: () => ({
    meta: [{ title: "Creer un compte · KALGA" }],
  }),
  component: SignupPage,
})

const MIN_PASSWORD = 8

function SignupPage() {
  const provision = useMutation(api.merchants.provisionMerchantOrg)

  const [shopName, setShopName] = useState("")
  const [phone, setPhone] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function validate(): string | null {
    if (shopName.trim().length < 2) {
      return "Indiquez le nom de votre boutique."
    }
    if (!isValidLocalPhone(phone)) {
      return "Entrez un numero WhatsApp valide."
    }
    if (password.length < MIN_PASSWORD) {
      return `Le mot de passe doit contenir au moins ${MIN_PASSWORD} caracteres.`
    }
    return null
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }

    const digits = toCanonicalPhone(phone)
    const name = shopName.trim()
    setLoading(true)

    try {
      const { error: signUpError } = await authClient.signUp.email({
        email: phoneToEmail(digits),
        password,
        name,
      })

      if (signUpError) {
        const code = signUpError.code ?? ""
        if (
          code.includes("EXIST") ||
          (signUpError.message ?? "").toLowerCase().includes("exist")
        ) {
          setError(
            "Un compte existe deja avec ce numero. Connectez-vous plutot.",
          )
        } else {
          setError(
            signUpError.message ?? "La creation du compte a echoue. Reessayez.",
          )
        }
        setLoading(false)
        return
      }

      // Compte cree + session active : on provisionne l'organisation + le marchand.
      await provision({ name, phone: digits })

      // Reload complet pour que le JWT re-porte `activeOrganizationId` cote Convex.
      window.location.href = "/app"
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Une erreur est survenue. Reessayez dans un instant.",
      )
      setLoading(false)
    }
  }

  return (
    <AuthShell
      rail="signup"
      title="Creez votre boutique"
      subtitle="Vendez sur WhatsApp en quelques minutes. Pas de carte bancaire."
      footer={
        <>
          Vous avez deja un compte ?{" "}
          <Link
            to="/login"
            className="font-medium text-primary-deep hover:underline"
          >
            Se connecter
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {error ? <AuthError>{error}</AuthError> : null}

        <div>
          <FieldLabel htmlFor="shop-name">Nom de la boutique</FieldLabel>
          <div className="relative">
            <Store className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-ink-faint" />
            <TextInput
              id="shop-name"
              value={shopName}
              onChange={(e) => setShopName(e.target.value)}
              disabled={loading}
              autoFocus
              placeholder="Chez Fatou"
              className="h-11 rounded-xl border-line bg-surface pl-10 text-base shadow-soft focus-visible:border-primary focus-visible:ring-[3px] focus-visible:ring-primary/15"
            />
          </div>
        </div>

        <div>
          <FieldLabel htmlFor="signup-phone">Numero WhatsApp</FieldLabel>
          <PhoneInput
            id="signup-phone"
            value={phone}
            onChange={setPhone}
            disabled={loading}
            hint="C'est le numero que vos clients verront. Aucun spam."
          />
        </div>

        <div>
          <FieldLabel htmlFor="signup-password">Mot de passe</FieldLabel>
          <PasswordInput
            id="signup-password"
            value={password}
            onChange={setPassword}
            disabled={loading}
            autoComplete="new-password"
            placeholder="Au moins 8 caracteres"
          />
          <p className="mt-2 text-xs text-ink-muted">
            Il vous servira a vous reconnecter depuis n'importe quel appareil.
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-1 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary text-base font-medium text-white shadow-soft transition-colors hover:bg-primary-deep disabled:pointer-events-none disabled:opacity-60"
        >
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Creation en cours...
            </>
          ) : (
            <>
              Creer mon compte
              <ArrowRight className="size-4" />
            </>
          )}
        </button>
      </form>
    </AuthShell>
  )
}
