/**
 * Client API — feature `stock`.
 * Réf : kalga-api/app/routers/stock.py (router monté sous /stock, sans /api).
 *
 * On passe par le proxy interne, qui route /api/proxy/stock/* → /stock/*
 * (cf. server/api/proxy/[...path].ts). Le code produit est transmis sans « # ».
 */

import type { RestockInput, StockCritique, StockMode, StockOverviewItem } from './types'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

/** Code sans « # » de tête (cohérent avec les autres endpoints produit). */
function bareCode(code: string): string {
  return code.replace(/^#/, '')
}

export const stockApi = {
  /** Vue d'ensemble du stock du marchand (table). */
  getOverview: (merchantId: number): Promise<StockOverviewItem[]> =>
    $fetch<StockOverviewItem[]>(proxyUrl(`/stock/merchant/${merchantId}/overview`)),

  /** Synthèse « stock critique » (compteurs + revenus perdus + produits). */
  getCritique: (merchantId: number): Promise<StockCritique> =>
    $fetch<StockCritique>(proxyUrl(`/stock/merchant/${merchantId}/critique`)),

  /** Change le mode appliqué en rupture pour un produit. */
  updateMode: (code: string, mode: StockMode, merchantId: number): Promise<unknown> =>
    $fetch(proxyUrl(`/stock/product/${bareCode(code)}/mode`), {
      method: 'PUT',
      body: { mode, merchant_id: merchantId },
    }),

  /** Réapprovisionne un produit (et notifie éventuellement la liste d'attente). */
  restock: (code: string, data: RestockInput): Promise<{ waitlist_notified?: number }> =>
    $fetch<{ waitlist_notified?: number }>(proxyUrl(`/stock/product/${bareCode(code)}/restock`), {
      method: 'PUT',
      body: data,
    }),
}
