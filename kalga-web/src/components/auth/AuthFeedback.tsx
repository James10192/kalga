import * as React from "react"
import { AlertCircle, CheckCircle2 } from "lucide-react"

/** Banniere d'erreur inline (rouge, tokens danger). */
export function AuthError({ children }: { children: React.ReactNode }) {
  if (!children) return null
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-xl border border-danger/25 bg-danger-tint px-3.5 py-2.5 text-sm text-danger"
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </div>
  )
}

/** Banniere de succes inline (vert, tokens primary). */
export function AuthSuccess({ children }: { children: React.ReactNode }) {
  if (!children) return null
  return (
    <div
      role="status"
      className="flex items-start gap-2 rounded-xl border border-primary/25 bg-primary-tint px-3.5 py-2.5 text-sm text-primary-deep"
    >
      <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </div>
  )
}
