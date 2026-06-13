import { Link } from "@tanstack/react-router"
import { Brand } from "./Brand"
import { ProfileMenu } from "./ProfileMenu"
import { authClient } from "@/lib/auth-client"

/**
 * En-tête de la landing : marque + liens d'ancre + zone d'auth.
 *
 * Auth-aware : connecte -> menu profil (avatar + tableau de bord + deconnexion) ;
 * deconnecte -> CTAs "Se connecter" / "Commencer".
 *
 * SSR-safe : pendant le SSR `session.data` est undefined, on rend les CTAs par
 * defaut puis on bascule cote client une fois la session resolue.
 */
export function Nav() {
  const session = authClient.useSession()
  const user = session.data?.user

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
          {user ? (
            <ProfileMenu
              name={user.name ?? ""}
              email={user.email ?? undefined}
            />
          ) : (
            <>
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
            </>
          )}
        </div>
      </div>
    </header>
  )
}
