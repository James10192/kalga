/**
 * Schémas Zod — feature `admin`.
 * Réf : GET /admin/dashboard (kalga-api/app/routers/admin.py).
 */

import { z } from 'zod'

const countSchema = z.number().int().min(0)

export const adminDashboardSchema = z.object({
  merchants: z.object({
    total: countSchema,
    active: countSchema,
    this_month: countSchema,
  }),
  conversations: z.object({
    total: countSchema,
    today: countSchema,
  }),
  messages: z.object({
    total: countSchema,
  }),
  sales: z.object({
    total: countSchema,
  }),
  subscriptions: z.object({
    by_plan: z.record(z.string(), countSchema),
    expiring_soon: countSchema,
  }),
})
