import { useEffect, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import { Settings, LogOut } from "lucide-react"
import { authClient } from "@/lib/auth-client"

/** Monogramme a partir du nom de la boutique (ex. "Chez Marcel" -> "CM"). */
function monogram(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return (name.trim() || "?").slice(0, 2).toUpperCase()
}

/**
 * Menu compte du dashboard marchand : bouton avatar (monogramme boutique) qui
 * ouvre un popover accessible (nom, lien Reglages, deconnexion).
 *
 * Popover maison, aucune dependance : ferme au clic exterieur et a Echap.
 * La deconnexion appelle `authClient.signOut()` puis recharge vers `/` pour
 * propager la fin de session au client Convex (JWT en cache).
 */
export function AccountMenu({ name }: { name: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onPointerDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
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

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Menu du compte"
        className="grid h-11 w-11 place-items-center rounded-full border border-primary/20 bg-primary-tint focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-page"
      >
        <span className="font-display text-[15px] font-bold text-primary-deep">
          {monogram(name)}
        </span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-xl border border-line bg-page shadow-lg"
        >
          <div className="border-b border-line px-4 py-3">
            <p className="truncate text-sm font-medium text-ink" title={name}>
              {name}
            </p>
          </div>

          <Link
            to="/app/settings"
            role="menuitem"
            onClick={() => setOpen(false)}
            className="flex h-11 items-center gap-3 px-4 text-sm text-ink hover:bg-secondary"
          >
            <Settings className="h-4 w-4 text-ink-muted" aria-hidden />
            Réglages
          </Link>

          <button
            type="button"
            role="menuitem"
            onClick={handleSignOut}
            className="flex h-11 w-full items-center gap-3 px-4 text-left text-sm text-ink hover:bg-secondary"
          >
            <LogOut className="h-4 w-4 text-ink-muted" aria-hidden />
            Se déconnecter
          </button>
        </div>
      )}
    </div>
  )
}
