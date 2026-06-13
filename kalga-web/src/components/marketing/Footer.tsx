import { Link } from "@tanstack/react-router"
import { Brand } from "./Brand"

/**
 * Pied de page de la landing : marque + colonnes de liens.
 * Les liens d'app pointent vers les vraies routes (/login, /signup, /app).
 */
export function Footer() {
  return (
    <footer className="bg-page">
      <div className="mx-auto max-w-6xl px-4 py-12 md:px-8">
        <div className="flex flex-col justify-between gap-8 md:flex-row">
          <div className="max-w-xs">
            <Brand />
            <p className="mt-3 text-sm text-ink-faint">
              Le commerce WhatsApp automatise, pense pour les marchands d'Afrique
              de l'Ouest.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-8 text-sm sm:grid-cols-3">
            <FooterCol title="Produit">
              <a href="#features" className="hover:text-ink">
                Fonctionnalites
              </a>
              <a href="#tarifs" className="hover:text-ink">
                Tarifs
              </a>
              <Link
                to="/boutique/$slug"
                params={{ slug: "chez-fatou" }}
                className="hover:text-ink"
              >
                Demo boutique
              </Link>
            </FooterCol>

            <FooterCol title="Compte">
              <Link to="/login" className="hover:text-ink">
                Se connecter
              </Link>
              <Link to="/signup" className="hover:text-ink">
                Creer un compte
              </Link>
            </FooterCol>

            <FooterCol title="Aide">
              <a
                href="https://wa.me/2250141540178"
                className="hover:text-ink"
              >
                Contact WhatsApp
              </a>
              <a href="#tarifs" className="hover:text-ink">
                Confidentialite
              </a>
            </FooterCol>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-line pt-6 text-xs text-ink-faint sm:flex-row">
          <p>2026 KALGA. Abidjan, Cote d'Ivoire.</p>
          <p>Fait pour les vendeurs, pas pour les developpeurs.</p>
        </div>
      </div>
    </footer>
  )
}

function FooterCol({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div>
      <p className="font-medium text-ink">{title}</p>
      <div className="mt-3 flex flex-col gap-2 text-ink-faint">{children}</div>
    </div>
  )
}
