/**
 * Tests Vitest — Schémas Zod feature conversations
 */

import { describe, expect, it } from 'vitest'

import {
  conversationListFilterSchema,
  conversationSchema,
  merchantReplyInputSchema,
  messageSchema,
} from '../../../../app/features/conversations/schemas'

const validConversation = {
  id: 1,
  merchant_id: 10,
  product_id: 5,
  client_phone: '2250161407534',
  client_name: 'Daisy',
  status: 'active',
  current_offer: null,
  selected_variant_id: null,
  created_at: '2026-06-01T10:00:00Z',
  updated_at: '2026-06-01T10:05:00Z',
}

describe('conversationSchema', () => {
  it('accepte une conversation valide', () => {
    const result = conversationSchema.safeParse(validConversation)
    expect(result.success).toBe(true)
  })

  it("rejette un téléphone trop court", () => {
    const result = conversationSchema.safeParse({ ...validConversation, client_phone: '123' })
    expect(result.success).toBe(false)
  })

  it("rejette un téléphone avec lettres", () => {
    const result = conversationSchema.safeParse({
      ...validConversation,
      client_phone: '225ABC4567',
    })
    expect(result.success).toBe(false)
  })

  it("accepte un statut 'negotiating'", () => {
    const result = conversationSchema.safeParse({
      ...validConversation,
      status: 'negotiating',
      current_offer: 18000,
    })
    expect(result.success).toBe(true)
  })

  it("rejette un statut inconnu", () => {
    const result = conversationSchema.safeParse({ ...validConversation, status: 'unknown_status' })
    expect(result.success).toBe(false)
  })

  it("accepte current_offer null", () => {
    const result = conversationSchema.safeParse({ ...validConversation, current_offer: null })
    expect(result.success).toBe(true)
  })
})

describe('messageSchema', () => {
  it('accepte un message valide', () => {
    const result = messageSchema.safeParse({
      id: 1,
      conversation_id: 10,
      content: 'Bonjour',
      is_from_client: true,
      created_at: '2026-06-01T10:00:00Z',
    })
    expect(result.success).toBe(true)
  })

  it("rejette un message qui dépasse MAX_LEN", () => {
    const result = messageSchema.safeParse({
      id: 1,
      conversation_id: 10,
      content: 'x'.repeat(2001),
      is_from_client: true,
      created_at: '2026-06-01T10:00:00Z',
    })
    expect(result.success).toBe(false)
  })
})

describe('merchantReplyInputSchema', () => {
  const valid = {
    merchant_id: 10,
    conversation_id: 5,
    client_phone: '2250161407534',
    client_question: 'Combien ça coûte ?',
    merchant_answer: 'C\'est 25000 F.',
    save_to_kb: true,
  }

  it('accepte une réponse valide', () => {
    const result = merchantReplyInputSchema.safeParse(valid)
    expect(result.success).toBe(true)
  })

  it("définit save_to_kb à true par défaut", () => {
    const { save_to_kb: _, ...sansFlag } = valid
    const result = merchantReplyInputSchema.safeParse(sansFlag)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.save_to_kb).toBe(true)
    }
  })

  it("rejette une réponse vide", () => {
    const result = merchantReplyInputSchema.safeParse({ ...valid, merchant_answer: '' })
    expect(result.success).toBe(false)
  })
})

describe('conversationListFilterSchema', () => {
  it("accepte un filtre vide", () => {
    const result = conversationListFilterSchema.safeParse({})
    expect(result.success).toBe(true)
  })

  it("accepte un filtre status", () => {
    const result = conversationListFilterSchema.safeParse({ status: 'pending_delivery' })
    expect(result.success).toBe(true)
  })
})
