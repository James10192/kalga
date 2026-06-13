import { Link } from "@tanstack/react-router"
import { Brand } from "./Brand"

/**
 * En-tête de la landing : marque + liens d'ancre + CTAs.
 * "Se connecter" mene a /login, "Commencer" mene a /signup.
 */
export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-page/90 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-8">
        <Link to="/" aria-label="Accueil KALGA">
          <Brand />
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-ink-muted md:flex">
          <a href="#how" className="hover:text-ink">
            Comment ca marche
          </a>
          <a href="#features" className="hover:text-ink">
            Fonctionnalites
          </a>
          <a href="#boutique" className="hover:text-ink">
            Boutique
          </a>
          <a href="#tarifs" className="hover:text-ink">
            Tarifs
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <Link
            to="/login"
            className="hidden h-11 items-center rounded-lg px-4 text-sm font-medium text-ink-muted hover:bg-secondary md:inline-flex"
          >
            Se connecter
          </Link>
          <Link
            to="/signup"
            className="inline-flex h-11 items-center rounded-lg bg-primary px-5 text-sm font-medium text-white hover:bg-primary-deep"
          >
            Commencer
          </Link>
        </div>
      </div>
    </header>
  )
}
