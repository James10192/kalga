import * as React from "react"
import { Eye, EyeOff } from "lucide-react"
import { cn } from "@/lib/utils"

interface PasswordInputProps {
  id?: string
  value: string
  onChange: (next: string) => void
  disabled?: boolean
  placeholder?: string
  autoComplete?: "current-password" | "new-password"
}

/** Champ mot de passe avec bascule de visibilite (oeil). */
export function PasswordInput({
  id,
  value,
  onChange,
  disabled,
  placeholder = "Votre mot de passe",
  autoComplete = "current-password",
}: PasswordInputProps) {
  const [visible, setVisible] = React.useState(false)
  return (
    <div
      className={cn(
        "flex h-11 items-center gap-2 rounded-xl border border-line bg-surface px-3.5 shadow-soft",
        "transition-[box-shadow,border-color] focus-within:border-primary focus-within:ring-[3px] focus-within:ring-primary/15",
        disabled && "pointer-events-none opacity-50",
      )}
    >
      <input
        id={id}
        type={visible ? "text" : "password"}
        autoComplete={autoComplete}
        disabled={disabled}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-full flex-1 bg-transparent text-base outline-none placeholder:text-ink-faint"
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
        className="grid size-7 shrink-0 place-items-center rounded-md text-ink-faint hover:bg-muted hover:text-ink"
      >
        {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  )
}
