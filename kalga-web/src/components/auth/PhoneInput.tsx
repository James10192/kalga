import * as React from "react"
import { ShieldCheck } from "lucide-react"
import { cn } from "@/lib/utils"
import { COUNTRY_CODE } from "./phone"

interface PhoneInputProps {
  id?: string
  /** Partie locale saisie (sans indicatif), ex `07 41 54 01 78`. */
  value: string
  onChange: (next: string) => void
  disabled?: boolean
  autoFocus?: boolean
  /** Petit texte de reassurance sous le champ (privacite). Optionnel. */
  hint?: string
}

/**
 * Champ numero WhatsApp avec selecteur d'indicatif (+225, fixe pour l'instant).
 * On stocke et expose la partie locale ; la conversion canonique
 * (`225XXXXXXXX`) se fait au submit via `toCanonicalPhone`.
 */
export function PhoneInput({
  id,
  value,
  onChange,
  disabled,
  autoFocus,
  hint = "Votre numero reste prive. Aucun spam.",
}: PhoneInputProps) {
  return (
    <div>
      <div
        className={cn(
          "flex h-11 items-center gap-2 rounded-xl border border-line bg-surface px-3.5 shadow-soft",
          "transition-[box-shadow,border-color] focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/15",
          disabled && "pointer-events-none opacity-50",
        )}
      >
        <span className="flex items-center gap-1.5 border-r border-line pr-3 text-sm font-medium text-ink">
          <span aria-hidden className="text-base">
            🇨🇮
          </span>
          <span className="tabular text-ink-muted">+{COUNTRY_CODE}</span>
        </span>
        <input
          id={id}
          inputMode="tel"
          autoComplete="tel-national"
          autoFocus={autoFocus}
          disabled={disabled}
          placeholder="07 41 54 01 78"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="tabular h-full flex-1 bg-transparent text-base outline-none placeholder:text-ink-faint"
        />
      </div>
      {hint ? (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-ink-muted">
          <ShieldCheck className="size-3.5" />
          {hint}
        </p>
      ) : null}
    </div>
  )
}
