/**
 * Tests Vitest — utils/nav.ts (intégrité des configs de navigation)
 *
 * On vérifie que chaque item de nav est bien formé (i18nKey + to + icon) et
 * que les zones exposent les entrées attendues. Garde-fou contre un item
 * cassé ou une route manquante.
 */

import { describe, expect, it } from 'vitest'

import { ADMIN_NAV, MERCHANT_NAV, PUBLIC_NAV, type NavItem } from '../../../app/utils/nav'

function assertWellFormed(items: ReadonlyArray<NavItem>): void {
  for (const item of items) {
    expect(typeof item.i18nKey).toBe('string')
    expect(item.i18nKey.length).toBeGreaterThan(0)
    expect(item.to.startsWith('/')).toBe(true)
    expect(item.icon.length).toBeGreaterThan(0)
  }
}

describe('nav configs', () => {
  it('MERCHANT_NAV : 5 entrées bien formées', () => {
    expect(MERCHANT_NAV).toHaveLength(5)
    assertWellFormed(MERCHANT_NAV)
    expect(MERCHANT_NAV.map((i) => i.i18nKey)).toContain('nav.products')
  })

  it('ADMIN_NAV : 4 entrées bien formées', () => {
    expect(ADMIN_NAV).toHaveLength(4)
    assertWellFormed(ADMIN_NAV)
    expect(ADMIN_NAV.map((i) => i.i18nKey)).toContain('nav.merchants')
  })

  it('PUBLIC_NAV : au moins l’accueil, bien formé', () => {
    expect(PUBLIC_NAV.length).toBeGreaterThanOrEqual(1)
    assertWellFormed(PUBLIC_NAV)
  })

  it('aucune route dupliquée au sein d’une même zone', () => {
    for (const zone of [MERCHANT_NAV, ADMIN_NAV, PUBLIC_NAV]) {
      const routes = zone.map((i) => i.to)
      expect(new Set(routes).size).toBe(routes.length)
    }
  })
})
