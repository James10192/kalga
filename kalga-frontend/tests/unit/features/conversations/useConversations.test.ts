/**
 * Tests Vitest — features/conversations/composables/useConversations.ts
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/vue-query', async () => (await import('../../helpers/tanstack')).tanstackMock)

import {
  fetchMock,
  invalidateQueries,
  resetTanstack,
  stubNuxtGlobals,
} from '../../helpers/tanstack'
import {
  conversationsKeys,
  useAcceptConversation,
  useConversationMessages,
  useConversationsList,
  useRejectConversation,
  useSendMerchantReply,
} from '../../../../app/features/conversations/composables/useConversations'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('conversationsKeys', () => {
  it('génère les clés de cache', () => {
    expect(conversationsKeys.all).toEqual(['conversations'])
    expect(conversationsKeys.list('225', 'active', 1)).toEqual([
      'conversations',
      'list',
      '225',
      'active',
      1,
    ])
    expect(conversationsKeys.list('225', undefined, 1)).toEqual([
      'conversations',
      'list',
      '225',
      'all',
      1,
    ])
    expect(conversationsKeys.detail(5)).toEqual(['conversations', 'detail', 5])
    expect(conversationsKeys.messages(5)).toEqual(['conversations', 'messages', 5])
  })
})

describe('queries conversations', () => {
  it('useConversationsList : clé + enabled selon phone non vide', async () => {
    const opts = useConversationsList('225', 'active', 1) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['conversations', 'list', '225', 'active', 1])
    expect(opts.enabled.value).toBe(true)
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
    expect((useConversationsList('', undefined, 1) as Record<string, any>).enabled.value).toBe(
      false,
    )
  })

  it('useConversationMessages : clé messages + queryFn', async () => {
    const opts = useConversationMessages(5) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['conversations', 'messages', 5])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})

describe('useSendMerchantReply', () => {
  it('envoie la réponse et invalide messages + détail + liste au succès', async () => {
    const opts = useSendMerchantReply() as Record<string, any>
    await opts.mutationFn({ conversation_id: 5, message: 'Bonjour' })
    expect(fetchMock).toHaveBeenCalledOnce()

    opts.onSuccess(undefined, { conversation_id: 5 })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['conversations', 'messages', 5] })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['conversations', 'detail', 5] })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['conversations', 'list'] })
  })
})

describe('useAcceptConversation / useRejectConversation', () => {
  it('accept appelle l’API et invalide les conversations', async () => {
    const opts = useAcceptConversation() as Record<string, any>
    await opts.mutationFn(5)
    expect(fetchMock).toHaveBeenCalledOnce()
    opts.onSuccess()
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['conversations'] })
  })

  it('reject appelle l’API et invalide les conversations', async () => {
    const opts = useRejectConversation() as Record<string, any>
    await opts.mutationFn(5)
    expect(fetchMock).toHaveBeenCalledOnce()
    opts.onSuccess()
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['conversations'] })
  })
})
