import { ImageIcon, MessageCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatAmount, initials } from "@/components/dashboard"

/**
 * Composants partagés du STOREFRONT public (plan 007).
 * Squelette KALGA constant, branté par marchand. Zéro chrome d'app
 * (pas de bottom-bar dashboard), mobile-first, SSR-safe (aucun accès
 * window/document au render).
 */

export type PublicMerchant = {
  id: string
  name: string
  phone: string
  slug: string
  tagline: string | null
  about: string | null
  logoPath: string | null
  bannerPath: string | null
  paymentMethods: string | null
}

export type PublicProduct = {
  id: string
  name: string
  code: string
  price: number
  description: string | null
  imagePath: string | null
  groupId: string | null
  variantName: string | null
  stockQuantity: number
  lowStockThreshold: number
}

export type StoreStock = "unlimited" | "ok" | "low_stock" | "out_of_stock"

const STOCK_LABEL: Record<StoreStock, string> = {
  unlimited: "Disponible",
  ok: "Disponible",
  low_stock: "Bientôt épuisé",
  out_of_stock: "Rupture",
}

const STOCK_DOT: Record<StoreStock, string> = {
  unlimited: "bg-primary",
  ok: "bg-primary",
  low_stock: "bg-nego",
  out_of_stock: "bg-danger",
}

/** État de stock public (parité backend, libellés orientés client). */
export function storeStock(p: Pick<PublicProduct, "stockQuantity" | "lowStockThreshold">): StoreStock {
  const q = p.stockQuantity ?? -1
  const t = p.lowStockThreshold ?? 5
  if (q === -1) return "unlimited"
  if (q === 0) return "out_of_stock"
  if (q <= t) return "low_stock"
  return "ok"
}

/**
 * Résout l'URL d'image. Le démo n'a pas d'images (placeholder).
 * Chemins absolus passés tels quels ; relatifs (legacy /uploads) à brancher
 * sur la base CDN en 009.
 */
export function resolveImageUrl(imagePath: string | null): string | null {
  if (!imagePath) return null
  if (/^https?:\/\//.test(imagePath)) return imagePath
  return null
}

/** Numéro WhatsApp normalisé (chiffres uniquement) pour wa.me. */
export function waNumber(phone: string): string {
  return phone.replace(/\D/g, "")
}

/** Construit un lien wa.me avec message pré-rempli. */
export function waLink(phone: string, text: string): string {
  return `https://wa.me/${waNumber(phone)}?text=${encodeURIComponent(text)}`
}

/** Pastille de stock (point + libellé). */
export function StockBadge({ stock }: { stock: StoreStock }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-surface/90 px-2.5 py-1 text-[11px] font-medium text-ink-muted backdrop-blur">
      <span className={cn("h-1.5 w-1.5 rounded-full", STOCK_DOT[stock])} />
      {STOCK_LABEL[stock]}
    </span>
  )
}

/** Logo boutique : image si dispo, sinon initiales sur fond vert tinté. */
export function StoreLogo({ merchant, size = 56 }: { merchant: PublicMerchant; size?: number }) {
  const url = resolveImageUrl(merchant.logoPath)
  if (url) {
    return (
      <img
        src={url}
        alt={merchant.name}
        width={size}
        height={size}
        className="rounded-2xl object-cover"
        style={{ width: size, height: size }}
      />
    )
  }
  return (
    <div
      className="grid place-items-center rounded-2xl bg-primary-tint font-display text-[18px] font-bold text-primary-deep"
      style={{ width: size, height: size }}
      aria-hidden
    >
      {initials(merchant.name) || merchant.name.slice(0, 2).toUpperCase()}
    </div>
  )
}

/**
 * En-tête de boutique : logo, nom, tagline, bouton WhatsApp.
 * Squelette constant KALGA, contenu branté par marchand.
 */
export function StoreHeader({ merchant }: { merchant: PublicMerchant }) {
  const text = `Bonjour ${merchant.name}, je viens de votre boutique en ligne.`
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-[960px] items-center gap-4 px-5 py-5">
        <StoreLogo merchant={merchant} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-[20px] font-bold leading-tight tracking-tight">
            {merchant.name}
          </h1>
          {merchant.tagline ? (
            <p className="mt-0.5 truncate text-[13.5px] text-ink-muted">
              {merchant.tagline}
            </p>
          ) : (
            <p className="mt-0.5 truncate text-[13.5px] text-ink-muted">
              Boutique en ligne
            </p>
          )}
        </div>
        <a
          href={waLink(merchant.phone, text)}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Contacter la boutique sur WhatsApp"
          className="inline-flex h-11 min-h-[48px] shrink-0 items-center gap-2 rounded-full bg-primary px-4 font-display text-[14px] font-bold text-primary-foreground shadow-soft transition active:scale-[0.97]"
        >
          <MessageCircle className="h-4.5 w-4.5" strokeWidth={2.5} />
          <span className="hidden sm:inline">WhatsApp</span>
        </a>
      </div>
    </header>
  )
}

/** Placeholder d'image produit (pas de photo). */
export function ImagePlaceholder({ className }: { className?: string }) {
  return (
    <div className={cn("grid place-items-center bg-page text-ink-faint", className)}>
      <ImageIcon className="h-8 w-8" />
    </div>
  )
}

/** Prix FCFA en Bricolage, tabular-nums. */
export function Price({ value, size = 16 }: { value: number; size?: number }) {
  return (
    <span className="font-display font-bold tabular" style={{ fontSize: size }}>
      {formatAmount(value)}{" "}
      <span className="text-[0.72em] font-semibold text-ink-muted">FCFA</span>
    </span>
  )
}

/** Pied de page boutique : signature KALGA + moyens de paiement. */
export function StoreFooter({ merchant }: { merchant: PublicMerchant }) {
  let methods: string[] = []
  if (merchant.paymentMethods) {
    try {
      const parsed = JSON.parse(merchant.paymentMethods)
      if (Array.isArray(parsed)) methods = parsed.map(String)
    } catch {
      methods = []
    }
  }
  if (methods.length === 0) methods = ["Wave", "Orange Money", "Espèces"]
  return (
    <footer className="mt-10 border-t border-line bg-surface">
      <div className="mx-auto max-w-[960px] px-5 py-8">
        <p className="text-[13px] text-ink-muted">Paiement</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {methods.map((m) => (
            <span
              key={m}
              className="inline-flex items-center rounded-full border border-line bg-page px-3 py-1.5 text-[12.5px] font-medium text-ink"
            >
              {m}
            </span>
          ))}
        </div>
        <p className="mt-6 text-[12px] text-ink-faint">
          Boutique propulsée par KALGA
        </p>
      </div>
    </footer>
  )
}
