/**
 * Regroupement des produits par variantes (group_id).
 * Référence : dashboard/static/app.js (renderProducts) — comportement 1:1.
 *
 * KALGA regroupe les produits partageant un `group_id` : une carte par groupe,
 * avec un produit « principal » (celui sans `variant_name`, sinon le premier) et
 * la liste de ses variantes. Les produits sans `group_id` forment leur propre
 * groupe d'une seule entrée.
 *
 * Générique : fonctionne pour tout objet portant { group_id, variant_name, name }
 * — produit dashboard (Product) comme produit vitrine (StorefrontProduct).
 * Fonction PURE (testée en isolation).
 */

/** Minimum requis pour regrouper par variante. */
export interface VariantGroupable {
  readonly group_id: string | null
  readonly variant_name: string | null
  readonly name: string
}

export interface ProductGroup<T extends VariantGroupable> {
  /** Produit représentatif du groupe (sans variant_name, sinon le premier). */
  readonly main: T
  /** Toutes les variantes du groupe (inclut `main`, longueur ≥ 1). */
  readonly variants: ReadonlyArray<T>
  /** Nom à afficher : nom du principal, sans suffixe « - variante ». */
  readonly displayName: string
}

/** Nom d'affichage d'un groupe (cf. app.js : strip du suffixe variante). */
function displayNameFor<T extends VariantGroupable>(main: T, variants: ReadonlyArray<T>): string {
  if (variants.length <= 1) return main.name
  const principal = variants.find((variant) => !variant.variant_name)
  return principal?.name ?? main.name.replace(/ - .+$/, '')
}

export function groupProductsByVariant<T extends VariantGroupable>(
  products: ReadonlyArray<T>,
): ProductGroup<T>[] {
  const groups: ProductGroup<T>[] = []
  const seenGroups = new Set<string>()

  for (const product of products) {
    if (product.group_id === null) {
      groups.push({ main: product, variants: [product], displayName: product.name })
      continue
    }

    if (seenGroups.has(product.group_id)) continue
    seenGroups.add(product.group_id)

    const variants = products.filter((candidate) => candidate.group_id === product.group_id)
    const main = variants.find((variant) => !variant.variant_name) ?? variants[0] ?? product
    groups.push({ main, variants, displayName: displayNameFor(main, variants) })
  }

  return groups
}
