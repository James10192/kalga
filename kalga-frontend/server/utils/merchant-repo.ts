/**
 * Client infra — marchand par téléphone (backend FastAPI).
 * Référence : backend `GET /api/merchants/{phone}`.
 *
 * Retourne `null` si aucun marchand pour ce numéro (404). Endpoint public côté
 * backend (les routes marchand ne sont pas protégées par JWT), donc pas de token.
 */

import type { MerchantRecord } from './merchant-session'

interface RawMerchant {
  id: number
  phone: string
  business_name?: string | null
  is_active?: boolean
}

export async function fetchMerchantByPhone(phone: string): Promise<MerchantRecord | null> {
  try {
    const data = await callBackend<RawMerchant>(`/api/merchants/${encodeURIComponent(phone)}`, {
      method: 'GET',
    })
    return {
      id: data.id,
      phone: data.phone,
      business_name: data.business_name ?? null,
      is_active: data.is_active ?? false,
    }
  } catch (error) {
    if (
      typeof error === 'object' &&
      error !== null &&
      'statusCode' in error &&
      (error as { statusCode?: number }).statusCode === 404
    ) {
      return null
    }
    throw error
  }
}
