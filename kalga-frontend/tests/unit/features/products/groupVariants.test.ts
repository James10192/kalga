/**
 * Tests Vitest — features/products/utils/groupVariants.ts
 *
 * Logique de regroupement par variantes (group_id), portée 1:1 depuis le
 * dashboard existant (dashboard/static/app.js renderProducts). Fonction pure
 * → testable en isolation. Couvre : sans groupe, groupe avec principal
 * explicite, groupe sans principal (fallback + suffixe), ordre.
 */

import { describe, expect, it } from 'vitest'

import { groupProductsByVariant } from '../../../../app/features/products/utils/groupVariants'
import type { Product } from '../../../../app/features/products/types'

function product(over: Partial<Product>): Product {
  return {
    id: 1,
    merchant_id: 10,
    code: '#K001',
    name: 'Produit',
    description: null,
    price: 1000,
    min_price: 800,
    image_path: null,
    group_id: null,
    variant_name: null,
    stock_quantity: null,
    low_stock_threshold: null,
    out_of_stock_mode: 'waitlist',
    is_available: true,
    created_at: '2026-01-01T00:00:00Z',
    ...over,
  }
}

describe('groupProductsByVariant', () => {
  it('retourne une liste vide pour aucune entrée', () => {
    expect(groupProductsByVariant([])).toEqual([])
  })

  it('un produit sans group_id forme son propre groupe', () => {
    const p = product({ id: 1, code: '#K001', name: 'Sac', group_id: null })
    const groups = groupProductsByVariant([p])
    expect(groups).toHaveLength(1)
    expect(groups[0]?.main).toBe(p)
    expect(groups[0]?.variants).toEqual([p])
    expect(groups[0]?.displayName).toBe('Sac')
  })

  it('regroupe les variantes par group_id ; le principal est celui sans variant_name', () => {
    const main = product({ id: 1, code: '#K001', name: 'Fruit ivoire', group_id: 'G1', variant_name: null })
    const v1 = product({ id: 2, code: '#K002', name: 'Fruit ivoire - camel', group_id: 'G1', variant_name: 'camel' })
    const v2 = product({ id: 3, code: '#K003', name: 'Fruit ivoire - orange', group_id: 'G1', variant_name: 'orange' })

    const groups = groupProductsByVariant([main, v1, v2])
    expect(groups).toHaveLength(1)
    expect(groups[0]?.main).toBe(main)
    expect(groups[0]?.variants).toHaveLength(3)
    expect(groups[0]?.displayName).toBe('Fruit ivoire')
  })

  it('sans principal explicite : prend le premier et retire le suffixe « - variante »', () => {
    const v1 = product({ id: 2, code: '#K002', name: 'Fruit ivoire - camel', group_id: 'G1', variant_name: 'camel' })
    const v2 = product({ id: 3, code: '#K003', name: 'Fruit ivoire - orange', group_id: 'G1', variant_name: 'orange' })

    const groups = groupProductsByVariant([v1, v2])
    expect(groups).toHaveLength(1)
    expect(groups[0]?.main).toBe(v1)
    expect(groups[0]?.displayName).toBe('Fruit ivoire')
  })

  it('mélange groupés et non groupés, dans l’ordre de première apparition', () => {
    const a = product({ id: 1, code: '#K001', name: 'Sac', group_id: null })
    const g1 = product({ id: 2, code: '#K002', name: 'Robe', group_id: 'G', variant_name: null })
    const g2 = product({ id: 3, code: '#K003', name: 'Robe - L', group_id: 'G', variant_name: 'L' })
    const b = product({ id: 4, code: '#K004', name: 'Montre', group_id: null })

    const groups = groupProductsByVariant([a, g1, g2, b])
    expect(groups.map((g) => g.displayName)).toEqual(['Sac', 'Robe', 'Montre'])
    expect(groups[1]?.variants).toHaveLength(2)
  })
})
