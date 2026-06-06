/**
 * Tests Vitest — composables/useAuth.ts
 *
 * `useAuth` dépend des auto-imports Nuxt `useUserSession`, `useRouter`,
 * `computed` (Vue) et `$fetch`. On les mocke via `vi.stubGlobal` (cf. roadmap
 * §7.6 : « Mock fetch via vi.fn() »). On vérifie les dérivés de rôle et les
 * effets de bord de login/logout (appels API, refresh session, redirection).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { computed, ref, type Ref } from 'vue'

import { ROLE } from '../../../app/utils/constants'
import { ROUTES } from '../../../app/utils/routes'
import { useAuth } from '../../../app/composables/useAuth'

type SessionUser = { id: number; email: string; role: string } | null

let userRef: Ref<SessionUser>
let loggedInRef: Ref<boolean>
let refreshSession: ReturnType<typeof vi.fn>
let clearSession: ReturnType<typeof vi.fn>
let routerPush: ReturnType<typeof vi.fn>
let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  userRef = ref<SessionUser>(null)
  loggedInRef = ref(false)
  refreshSession = vi.fn().mockResolvedValue(undefined)
  clearSession = vi.fn().mockResolvedValue(undefined)
  routerPush = vi.fn().mockResolvedValue(undefined)
  fetchMock = vi.fn()

  vi.stubGlobal('computed', computed)
  vi.stubGlobal('useUserSession', () => ({
    user: userRef,
    loggedIn: loggedInRef,
    fetch: refreshSession,
    clear: clearSession,
  }))
  vi.stubGlobal('useRouter', () => ({ push: routerPush }))
  vi.stubGlobal('$fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useAuth — dérivés de rôle', () => {
  it('isAdmin vrai uniquement pour le rôle admin', () => {
    userRef.value = { id: 1, email: 'a@kalga.com', role: ROLE.ADMIN }
    const { isAdmin, isMerchant } = useAuth()
    expect(isAdmin.value).toBe(true)
    expect(isMerchant.value).toBe(false)
  })

  it('isMerchant vrai uniquement pour le rôle merchant', () => {
    userRef.value = { id: 2, email: 'm@kalga.com', role: ROLE.MERCHANT }
    const { isAdmin, isMerchant } = useAuth()
    expect(isAdmin.value).toBe(false)
    expect(isMerchant.value).toBe(true)
  })

  it('isAdmin/isMerchant faux quand pas de session', () => {
    const { isAdmin, isMerchant } = useAuth()
    expect(isAdmin.value).toBe(false)
    expect(isMerchant.value).toBe(false)
  })

  it('expose isLoggedIn depuis la session', () => {
    loggedInRef.value = true
    const { isLoggedIn } = useAuth()
    expect(isLoggedIn.value).toBe(true)
  })
})

describe('useAuth — login', () => {
  it('poste les credentials sur /api/auth/login, rafraîchit la session et renvoie la réponse', async () => {
    const response = { user: { id: 1, email: 'a@kalga.com', role: ROLE.ADMIN } }
    fetchMock.mockResolvedValue(response)

    const { login } = useAuth()
    const credentials = { email: 'a@kalga.com', password: 'secret123' }
    const result = await login(credentials)

    expect(fetchMock).toHaveBeenCalledWith('/api/auth/login', {
      method: 'POST',
      body: credentials,
    })
    expect(refreshSession).toHaveBeenCalledOnce()
    expect(result).toEqual(response)
  })

  it('propage l’erreur si le login échoue (sans rafraîchir la session)', async () => {
    fetchMock.mockRejectedValue(new Error('401'))
    const { login } = useAuth()

    await expect(login({ email: 'x@kalga.com', password: 'bad' })).rejects.toThrow('401')
    expect(refreshSession).not.toHaveBeenCalled()
  })
})

describe('useAuth — logout', () => {
  it('poste sur /api/auth/logout, vide la session et redirige vers login', async () => {
    fetchMock.mockResolvedValue(undefined)
    const { logout } = useAuth()

    await logout()

    expect(fetchMock).toHaveBeenCalledWith('/api/auth/logout', { method: 'POST' })
    expect(clearSession).toHaveBeenCalledOnce()
    expect(routerPush).toHaveBeenCalledWith(ROUTES.login)
  })
})
