/**
 * Tests Vitest — server/utils/merchant-session.ts (service pur, TDD).
 *
 * `resolveMerchantSession` est une fonction métier pure à dépendances injectées
 * (statut bridge + marchand backend) → testable en isolation avec des fakes,
 * sans runtime Nitro ni réseau. Couvre les frontières : non connecté, marchand
 * introuvable, actif, suspendu.
 */

import { describe, expect, it, vi } from 'vitest'

import {
  MerchantNotFoundError,
  resolveMerchantSession,
  WhatsappNotConnectedError,
  type MerchantSessionDeps,
} from '../../../server/utils/merchant-session'

const MERCHANT = {
  id: 7,
  phone: '225161407534',
  business_name: 'Fleurs d Abidjan',
  is_active: true,
}

function makeDeps(over: Partial<MerchantSessionDeps> = {}): MerchantSessionDeps {
  return {
    getStatus: vi.fn().mockResolvedValue({ connected: true }),
    getMerchant: vi.fn().mockResolvedValue(MERCHANT),
    ...over,
  }
}

describe('resolveMerchantSession', () => {
  it('rejette si le bridge ne connaît pas ce numéro (status null) — sans charger le marchand', async () => {
    const deps = makeDeps({ getStatus: vi.fn().mockResolvedValue(null) })
    await expect(resolveMerchantSession('225161407534', deps)).rejects.toBeInstanceOf(
      WhatsappNotConnectedError,
    )
    expect(deps.getMerchant).not.toHaveBeenCalled()
  })

  it('rejette si WhatsApp non connecté (connected=false)', async () => {
    const deps = makeDeps({ getStatus: vi.fn().mockResolvedValue({ connected: false }) })
    await expect(resolveMerchantSession('225161407534', deps)).rejects.toBeInstanceOf(
      WhatsappNotConnectedError,
    )
  })

  it('rejette si le marchand est introuvable côté backend', async () => {
    const deps = makeDeps({ getMerchant: vi.fn().mockResolvedValue(null) })
    await expect(resolveMerchantSession('225161407534', deps)).rejects.toBeInstanceOf(
      MerchantNotFoundError,
    )
  })

  it('retourne un user marchand pour un marchand actif et connecté', async () => {
    const deps = makeDeps()
    const user = await resolveMerchantSession('225161407534', deps)
    expect(user).toEqual({
      id: 7,
      email: null,
      role: 'merchant',
      is_active: true,
      merchant_id: 7,
      merchant_phone: '225161407534',
      business_name: 'Fleurs d Abidjan',
    })
    expect(deps.getStatus).toHaveBeenCalledWith('225161407534')
  })

  it('crée quand même la session pour un marchand suspendu (le middleware redirige vers /account-suspended)', async () => {
    const deps = makeDeps({
      getMerchant: vi.fn().mockResolvedValue({ ...MERCHANT, is_active: false }),
    })
    const user = await resolveMerchantSession('225161407534', deps)
    expect(user.is_active).toBe(false)
    expect(user.role).toBe('merchant')
  })
})
