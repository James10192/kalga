import { useEffect, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import { LayoutDashboard, LogOut } from "lucide-react"
import { authClient } from "@/lib/auth-client"

type ProfileMenuProps = {
  /** Nom de la boutique ou de l'utilisateur connecte. */
  name: string
  /** Email, sert de repli pour le monogramme et l'affichage. */
  email?: string
}

/** Construit un monogramme a partir du nom (ou de l'email). */
function monogram(name: string, email?: string): string {
  const source = name.trim() || email?.trim() || "?"
  const parts = source.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return source.slice(0, 2).toUpperCase()
}

/**
 * Popover de profil pour la landing connectee : bouton avatar (monogramme)
 * qui ouvre un menu accessible (nom, lien tableau de bord, deconnexion).
 *
 * Popover maison : pas de dependance. Ferme au clic exterieur et a Echap.
 */
export function ProfileMenu({ name, email }: ProfileMenuProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return

    function onPointerDown(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false)
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false)
    }

    document.addEventListener("mousedown", onPointerDown)
    document.addEventListener("keydown", onKeyDown)
    return () => {
      document.removeEventListener("mousedown", onPointerDown)
      document.removeEventListener("keydown", onKeyDown)
    }
  }, [open])

  async function handleSignOut() {
    await authClient.signOut()
    window.location.href = "/"
  }

  const label = name.trim() || email || "Mon compte"

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Ouvrir le menu du profil"
        className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-primary text-sm font-semibold text-white hover:bg-primary-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-page"
      >
        {monogram(name, email)}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-60 overflow-hidden rounded-xl border border-line bg-page shadow-lg"
        >
          <div className="border-b border-line px-4 py-3">
            <p className="truncate text-sm font-medium text-ink" title={label}>
              {label}
            </p>
            {email && name.trim() && email !== name.trim() && (
              <p className="truncate text-xs text-ink-muted" title={email}>
                {email}
              </p>
            )}
          </div>

          <Link
            to="/app"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="flex h-11 items-center gap-3 px-4 text-sm text-ink hover:bg-secondary"
          >
            <LayoutDashboard className="h-4 w-4 text-ink-muted" aria-hidden />
            Mon tableau de bord
          </Link>

          <button
            type="button"
            role="menuitem"
            onClick={handleSignOut}
            className="flex h-11 w-full items-center gap-3 px-4 text-left text-sm text-ink hover:bg-secondary"
          >
            <LogOut className="h-4 w-4 text-ink-muted" aria-hidden />
            Se deconnecter
          </button>
        </div>
      )}
    </div>
  )
}
