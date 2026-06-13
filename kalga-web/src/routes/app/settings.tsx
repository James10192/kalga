import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import {
  Bot,
  Store,
  KeyRound,
  Mail,
  QrCode,
  CircleCheckBig,
  Copy,
  Check,
  ExternalLink,
  LogOut,
} from "lucide-react"
import { authClient } from "@/lib/auth-client"
import { api } from "../../../convex/_generated/api"
import type { Doc } from "../../../convex/_generated/dataModel"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { formatAmount } from "@/components/dashboard"

/**
 * Écran "Réglages" du dashboard marchand.
 *
 * Sections (DIRECTION.md) : persona du bot (ton/style/catchphrase), boutique
 * (slug {slug}.kalga.app + infos), connexion (email + mot de passe, formulaire),
 * code d'activation (champ + état abonnement actif/expiré via api), statut
 * WhatsApp (connecté / QR à scanner — placeholder).
 *
 * Câblé aux données Convex LIVE scopées au marchand courant via withOrg
 * (merchants.currentMerchant + settings.billingForCurrentMerchant : aucun
 * `merchantId` venant du client = anti-fuite cross-tenant). Les soumissions de
 * formulaires sont des stubs pour l'instant (mutations withOrg à venir) :
 * la structure (react-hook-form + zod) se branchera dessus sans réécriture.
 *
 * Responsive : mobile = sections empilées ; >= lg = grille deux colonnes.
 */
export const Route = createFileRoute("/app/settings")({
  component: SettingsPage,
})

function SettingsPage() {
  const merchant = useQuery(api.merchants.currentMerchant, {})

  if (merchant === undefined) return <SettingsLoading />
  if (merchant === null) return <SettingsMerchantMissing />

  return <SettingsContent merchant={merchant} />
}

function SettingsContent({ merchant }: { merchant: Doc<"merchants"> }) {
  const billing = useQuery(api.settings.billingForCurrentMerchant, {})

  return (
    <div className="mx-auto w-full max-w-6xl">
      <Header />
      <div className="grid grid-cols-1 gap-5 px-5 pb-8 pt-1 lg:grid-cols-2 lg:items-start">
        <PersonaSection merchant={merchant} />
        <BoutiqueSection merchant={merchant} />
        <ConnexionSection />
        <ActivationSection billing={billing} />
        <WhatsappSection />
        <DeconnexionSection />
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * Compte — deconnexion (point canonique mobile : accessible via l'onglet Réglages)
 * ────────────────────────────────────────────────────────────────────────── */
function DeconnexionSection() {
  async function handleSignOut() {
    await authClient.signOut()
    window.location.href = "/"
  }

  return (
    <Section
      icon={LogOut}
      title="Compte"
      description="Gérer votre session sur cet appareil."
    >
      <Button
        type="button"
        variant="outline"
        onClick={handleSignOut}
        className="h-11 w-full rounded-xl"
      >
        <LogOut className="h-4 w-4" />
        Se déconnecter
      </Button>
    </Section>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * Coquille de section : carte surface, titre + icône, contenu.
 * ────────────────────────────────────────────────────────────────────────── */
function Section({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Bot
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary-tint text-primary-deep">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-[16px] font-bold leading-tight">
            {title}
          </h2>
          {description && (
            <p className="mt-0.5 text-[13px] text-ink-muted">{description}</p>
          )}
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * 1. Persona du bot — ton / style / catchphrase
 * ────────────────────────────────────────────────────────────────────────── */
const TONE_OPTIONS = [
  { value: "casual", label: "Décontracté" },
  { value: "friendly", label: "Chaleureux" },
  { value: "formal", label: "Formel" },
  { value: "professional", label: "Professionnel" },
] as const

const STYLE_OPTIONS = [
  { value: "flexible", label: "Flexible" },
  { value: "firm", label: "Ferme" },
  { value: "playful", label: "Joueur" },
] as const

const personaSchema = z.object({
  tone: z.enum(["casual", "friendly", "formal", "professional"]),
  style: z.enum(["flexible", "firm", "playful"]),
  catchphrase: z.string().max(120, "120 caractères maximum").optional(),
})

function PersonaSection({ merchant }: { merchant: Doc<"merchants"> }) {
  const [saved, setSaved] = useState(false)
  const form = useForm<z.infer<typeof personaSchema>>({
    resolver: zodResolver(personaSchema),
    defaultValues: {
      tone: merchant.botTone ?? "casual",
      style: merchant.botStyle ?? "flexible",
      catchphrase: merchant.botCatchphrase ?? "",
    },
  })

  function onSubmit() {
    // Stub : la mutation scopée withOrg arrive avec l'OTP live.
    setSaved(true)
    setTimeout(() => setSaved(false), 2200)
  }

  return (
    <Section
      icon={Bot}
      title="Persona du bot"
      description="La voix de votre vendeur automatique sur WhatsApp."
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="tone"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Ton</FormLabel>
                <FormControl>
                  <ChoiceRow
                    options={TONE_OPTIONS}
                    value={field.value}
                    onChange={field.onChange}
                  />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="style"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Style de négociation</FormLabel>
                <FormControl>
                  <ChoiceRow
                    options={STYLE_OPTIONS}
                    value={field.value}
                    onChange={field.onChange}
                  />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="catchphrase"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Phrase signature</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="On trouve toujours un terrain d'entente !"
                    className="h-11 rounded-xl"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <SaveBar saved={saved} />
        </form>
      </Form>
    </Section>
  )
}

/** Rangée de choix en pills (radio visuel, accent vert pour l'actif). */
function ChoiceRow<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            aria-pressed={active}
            className={
              active
                ? "min-h-11 rounded-full border border-primary/25 bg-primary-tint px-4 text-[14px] font-semibold text-primary-deep"
                : "min-h-11 rounded-full border border-line bg-surface px-4 text-[14px] font-medium text-ink-muted transition active:scale-[0.98]"
            }
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * 2. Boutique — slug {slug}.kalga.app + infos
 * ────────────────────────────────────────────────────────────────────────── */
const boutiqueSchema = z.object({
  businessName: z.string().min(1, "Le nom est requis").max(80),
  tagline: z.string().max(80).optional(),
  address: z.string().max(120).optional(),
})

function BoutiqueSection({ merchant }: { merchant: Doc<"merchants"> }) {
  const [saved, setSaved] = useState(false)
  const form = useForm<z.infer<typeof boutiqueSchema>>({
    resolver: zodResolver(boutiqueSchema),
    defaultValues: {
      businessName: merchant.businessName ?? merchant.name ?? "",
      tagline: merchant.tagline ?? "",
      address: merchant.address ?? "",
    },
  })

  function onSubmit() {
    setSaved(true)
    setTimeout(() => setSaved(false), 2200)
  }

  return (
    <Section
      icon={Store}
      title="Boutique"
      description="Vos informations publiques et votre adresse en ligne."
    >
      <StorefrontUrl slug={merchant.slug} />
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="mt-4 space-y-4">
          <FormField
            control={form.control}
            name="businessName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Nom de la boutique</FormLabel>
                <FormControl>
                  <Input {...field} className="h-11 rounded-xl" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="tagline"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Slogan</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="La mode à petit prix"
                    className="h-11 rounded-xl"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="address"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Adresse</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="Cocody, Abidjan"
                    className="h-11 rounded-xl"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <SaveBar saved={saved} />
        </form>
      </Form>
    </Section>
  )
}

/** Affiche l'URL publique {slug}.kalga.app, copiable. */
function StorefrontUrl({ slug }: { slug: string }) {
  const [copied, setCopied] = useState(false)
  const url = `${slug}.kalga.app`

  function copy() {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(`https://${url}`).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 1800)
      })
    }
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-line bg-page px-3.5 py-3">
      <div className="min-w-0">
        <p className="text-[12px] text-ink-muted">Adresse de votre vitrine</p>
        <p className="mt-0.5 truncate font-mono text-[14px] font-medium text-ink">
          {url}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <button
          type="button"
          onClick={copy}
          aria-label="Copier l'adresse"
          className="grid h-10 w-10 place-items-center rounded-full text-ink-muted transition active:scale-95"
        >
          {copied ? (
            <Check className="h-[18px] w-[18px] text-primary-deep" />
          ) : (
            <Copy className="h-[18px] w-[18px]" />
          )}
        </button>
        <a
          href={`https://${url}`}
          target="_blank"
          rel="noreferrer"
          aria-label="Ouvrir la vitrine"
          className="grid h-10 w-10 place-items-center rounded-full text-ink-muted transition active:scale-95"
        >
          <ExternalLink className="h-[18px] w-[18px]" />
        </a>
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * 3. Connexion — ajouter email + mot de passe
 * ────────────────────────────────────────────────────────────────────────── */
const connexionSchema = z
  .object({
    email: z.string().email("Adresse e-mail invalide"),
    password: z.string().min(8, "8 caractères minimum"),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: "Les mots de passe ne correspondent pas",
    path: ["confirm"],
  })

function ConnexionSection() {
  const [saved, setSaved] = useState(false)
  const form = useForm<z.infer<typeof connexionSchema>>({
    resolver: zodResolver(connexionSchema),
    defaultValues: { email: "", password: "", confirm: "" },
  })

  function onSubmit() {
    // Stub : la liaison Better Auth (email+password) arrive avec l'OTP live.
    setSaved(true)
    setTimeout(() => setSaved(false), 2200)
    form.reset()
  }

  return (
    <Section
      icon={KeyRound}
      title="Connexion"
      description="Ajoutez un e-mail et un mot de passe pour vous connecter sans WhatsApp."
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Adresse e-mail</FormLabel>
                <FormControl>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-ink-faint" />
                    <Input
                      {...field}
                      type="email"
                      inputMode="email"
                      autoComplete="email"
                      placeholder="vous@exemple.com"
                      className="h-11 rounded-xl pl-10"
                    />
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Mot de passe</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="password"
                    autoComplete="new-password"
                    placeholder="Au moins 8 caractères"
                    className="h-11 rounded-xl"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="confirm"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Confirmer le mot de passe</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="password"
                    autoComplete="new-password"
                    className="h-11 rounded-xl"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <SaveBar saved={saved} label="Enregistrer la connexion" />
        </form>
      </Form>
    </Section>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * 4. Code d'activation + état de l'abonnement
 * ────────────────────────────────────────────────────────────────────────── */
type Billing = {
  subscription: {
    plan: "trial" | "starter" | "pro" | "enterprise"
    status: "active" | "expired"
    startDate: number | null
    endDate: number | null
    trialEndsAt: number | null
    messagesLimit: number | null
    messagesUsed: number | null
    productsLimit: number | null
  } | null
  activationCode: {
    code: string
    status: "pending" | "used" | "expired"
    usedAt: number | null
    expiresAt: number | null
  } | null
}

const PLAN_LABELS: Record<string, string> = {
  trial: "Essai",
  starter: "Starter",
  pro: "Pro",
  enterprise: "Entreprise",
}

const activationSchema = z.object({
  code: z
    .string()
    .min(6, "Code trop court")
    .max(12, "Code trop long")
    .transform((s) => s.toUpperCase().trim()),
})

function ActivationSection({ billing }: { billing: Billing | undefined }) {
  const [feedback, setFeedback] = useState<string | null>(null)
  const form = useForm<z.infer<typeof activationSchema>>({
    resolver: zodResolver(activationSchema),
    defaultValues: { code: "" },
  })

  function onSubmit() {
    // Stub : l'activation réelle (mutation + audit) arrive en back-office 008.
    setFeedback("Code reçu. La validation sera disponible très bientôt.")
    setTimeout(() => setFeedback(null), 3200)
    form.reset()
  }

  return (
    <Section
      icon={KeyRound}
      title="Abonnement"
      description="Activez votre abonnement avec le code reçu après paiement (Wave / Orange Money)."
    >
      {billing === undefined ? (
        <SubscriptionSkeleton />
      ) : (
        <SubscriptionState billing={billing} />
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="mt-4 space-y-3">
          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Code d'activation</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder="KALGA-XXXX"
                    autoCapitalize="characters"
                    className="h-11 rounded-xl font-mono tracking-widest uppercase"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" size="lg" className="h-11 w-full rounded-xl">
            Activer
          </Button>
          {feedback && (
            <p className="text-center text-[13px] font-medium text-primary-deep">
              {feedback}
            </p>
          )}
        </form>
      </Form>
    </Section>
  )
}

/** Bandeau d'état de l'abonnement (actif/expiré) + détails plan. */
function SubscriptionState({ billing }: { billing: Billing }) {
  const sub = billing.subscription
  if (!sub) {
    return (
      <div className="rounded-xl border border-line bg-page px-4 py-3.5">
        <p className="text-[14px] font-medium text-ink">
          Aucun abonnement actif
        </p>
        <p className="mt-0.5 text-[13px] text-ink-muted">
          Entrez un code d'activation pour démarrer.
        </p>
      </div>
    )
  }

  const active = sub.status === "active"
  const planLabel = PLAN_LABELS[sub.plan] ?? sub.plan
  const expiry = sub.trialEndsAt ?? sub.endDate
  const messagesUsed = sub.messagesUsed ?? 0
  const messagesLimit = sub.messagesLimit ?? null

  return (
    <div
      className={
        active
          ? "rounded-xl border border-primary/20 bg-primary-tint px-4 py-3.5"
          : "rounded-xl border border-danger/20 bg-danger-tint px-4 py-3.5"
      }
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-display text-[15px] font-bold text-ink">
          Plan {planLabel}
        </span>
        <span
          className={
            active
              ? "inline-flex items-center gap-1 rounded-full bg-surface px-2.5 py-1 text-[12px] font-semibold text-primary-deep"
              : "inline-flex items-center gap-1 rounded-full bg-surface px-2.5 py-1 text-[12px] font-semibold text-danger"
          }
        >
          {active && <CircleCheckBig className="h-3.5 w-3.5" />}
          {active ? "Actif" : "Expiré"}
        </span>
      </div>

      {expiry && (
        <p className="mt-1.5 text-[13px] text-ink-muted">
          {active
            ? `Valable jusqu'au ${formatDate(expiry)}`
            : `Expiré le ${formatDate(expiry)}`}
        </p>
      )}

      {messagesLimit !== null && (
        <p className="mt-0.5 text-[13px] text-ink-muted tabular">
          {formatAmount(messagesUsed)} / {formatAmount(messagesLimit)} messages
          utilisés
        </p>
      )}
    </div>
  )
}

function SubscriptionSkeleton() {
  return (
    <div className="rounded-xl border border-line bg-page px-4 py-3.5">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <Skeleton className="mt-2.5 h-3.5 w-40" />
      <Skeleton className="mt-2 h-3.5 w-32" />
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * 5. Statut WhatsApp — connecté / QR à scanner (placeholder)
 * ────────────────────────────────────────────────────────────────────────── */
function WhatsappSection() {
  // Placeholder : le statut réel (bridge Baileys) sera câblé via une query
  // dédiée. On présente l'état "connecté" du marchand démo, et le bloc QR
  // pour le cas non connecté (structure prête à brancher).
  const connected = true

  return (
    <Section
      icon={QrCode}
      title="WhatsApp"
      description="Le canal par lequel votre bot vend et négocie."
    >
      {connected ? (
        <div className="flex items-center gap-3 rounded-xl border border-primary/20 bg-primary-tint px-4 py-3.5">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-surface text-primary-deep">
            <CircleCheckBig className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-[14px] font-semibold text-ink">
              WhatsApp connecté
            </p>
            <p className="mt-0.5 text-[13px] text-ink-muted">
              Votre bot reçoit et répond aux messages.
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-line bg-page p-5 text-center">
          <div className="mx-auto grid h-36 w-36 place-items-center rounded-2xl border border-line bg-surface">
            <QrCode className="h-20 w-20 text-ink-faint" />
          </div>
          <p className="mt-3 text-[14px] font-semibold text-ink">
            Scannez le QR code
          </p>
          <p className="mt-1 text-[13px] text-ink-muted">
            Ouvrez WhatsApp, puis Appareils connectés, et scannez ce code pour
            relier votre numéro.
          </p>
        </div>
      )}
    </Section>
  )
}

/* ──────────────────────────────────────────────────────────────────────────
 * Briques partagées
 * ────────────────────────────────────────────────────────────────────────── */

/** Barre d'enregistrement : bouton + confirmation discrète. */
function SaveBar({
  saved,
  label = "Enregistrer",
}: {
  saved: boolean
  label?: string
}) {
  return (
    <div className="flex items-center gap-3 pt-1">
      <Button type="submit" size="lg" className="h-11 rounded-xl px-6">
        {label}
      </Button>
      {saved && (
        <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary-deep">
          <Check className="h-4 w-4" /> Enregistré
        </span>
      )}
    </div>
  )
}

function Header() {
  return (
    <header className="px-5 pb-3 pt-4">
      <p className="text-[13px] text-ink-muted">Votre boutique, votre bot</p>
      <h1 className="font-display text-[22px] font-bold leading-tight tracking-tight">
        Réglages
      </h1>
    </header>
  )
}

/** Date courte chaleureuse (12 juin 2026). */
function formatDate(epochMs: number): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(epochMs))
}

/* ── États plein écran ────────────────────────────────────────────────────── */

function SettingsLoading() {
  return (
    <>
      <header className="px-5 pb-3 pt-4">
        <Skeleton className="h-3.5 w-36" />
        <Skeleton className="mt-1.5 h-6 w-28" />
      </header>
      <div className="space-y-5 px-5 pb-8 pt-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="rounded-2xl border border-line bg-surface p-5 shadow-card"
          >
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <Skeleton className="h-11 w-full rounded-xl" />
              <Skeleton className="h-11 w-2/3 rounded-xl" />
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

function SettingsMerchantMissing() {
  return (
    <div className="px-5 py-16 text-center">
      <p className="font-display text-[18px] font-bold">Boutique introuvable</p>
      <p className="mt-2 text-[14px] text-ink-muted">
        Votre compte n'est pas encore relié à une boutique. Terminez la création
        de votre compte pour accéder à vos réglages.
      </p>
    </div>
  )
}
