/**
 * Types génériques d'API — KALGA Frontend
 * Référence : ARCHITECTURE_FRONTEND.md sections 5.4 (SSOT) + 7.2 (Data fetching)
 *
 * Ces types sont AGNOSTIQUES du domaine métier. Ils représentent la forme
 * des réponses du proxy /api/proxy/* (qui relaie vers le backend FastAPI).
 */

// =============================================================================
// RÉPONSES API
// =============================================================================

/** Réponse de succès générique */
export interface ApiSuccess<T> {
  readonly status: 'success'
  readonly data: T
}

/** Erreur API structurée (alignée sur FastAPI HTTPException) */
export interface ApiError {
  readonly status: 'error'
  readonly detail: string
  readonly code?: string
  /** Pour les erreurs de validation Zod/Pydantic : champ concerné */
  readonly field?: string
  /** Pour les erreurs de validation : liste détaillée */
  readonly errors?: ReadonlyArray<ValidationFieldError>
}

/** Détail d'une erreur de validation côté serveur */
export interface ValidationFieldError {
  readonly field: string
  readonly message: string
  readonly code?: string
}

/** Union discriminée pour TOUTE réponse API */
export type ApiResponse<T> = ApiSuccess<T> | ApiError

// =============================================================================
// TYPE GUARDS (narrowing)
// =============================================================================

/** Type guard : la réponse a réussi */
export function isApiSuccess<T>(res: ApiResponse<T>): res is ApiSuccess<T> {
  return res.status === 'success'
}

/** Type guard : la réponse est une erreur */
export function isApiError<T>(res: ApiResponse<T>): res is ApiError {
  return res.status === 'error'
}

// =============================================================================
// PAGINATION
// =============================================================================

/** Paramètres standards d'une requête liste */
export interface ListParams {
  readonly page?: number
  readonly per_page?: number
  readonly search?: string
}

/** Résultat paginé typé */
export interface Paginated<T> {
  readonly items: ReadonlyArray<T>
  readonly total: number
  readonly page: number
  readonly per_page: number
  readonly total_pages: number
}

// =============================================================================
// HTTP — types utilitaires
// =============================================================================

/** Méthodes HTTP supportées par notre client API */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

/** Identifiant d'entité métier (PK serveur) */
export type EntityId = number

/** Timestamp ISO 8601 (vient du backend en string) */
export type IsoDate = string

/** UUID v4 string (pour group_id de variantes par ex.) */
export type Uuid = string
