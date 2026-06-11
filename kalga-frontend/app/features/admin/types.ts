/**
 * Types inférés — feature `admin`.
 */

import type { z } from 'zod'

import type { adminDashboardSchema } from './schemas'

export type AdminDashboard = z.infer<typeof adminDashboardSchema>
