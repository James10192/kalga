/**
 * Composable de notifications toast — feedback UX (succès, erreur, info).
 * Référence : ARCHITECTURE_FRONTEND.md section 7.9 (error handling)
 *
 * Usage :
 *   const { push } = useToast()
 *   push.success(t('products.createSuccess'))
 *   push.error(extractApiErrorMessage(err, t('common.error')))
 *
 * État partagé entre tous les composants via `useState` (équivalent Pinia
 * léger fourni par Nuxt). Le rendu se fait via `<ToastContainer />` monté
 * une seule fois dans chaque layout protégé.
 */

export type ToastType = 'success' | 'error' | 'info'

export interface Toast {
  readonly id: string
  readonly type: ToastType
  readonly message: string
}

const TOAST_TTL_MS = 4000
const MAX_TOASTS = 5

let counter = 0

function generateId(): string {
  counter += 1
  return `toast-${counter}-${Date.now().toString(36)}`
}

export function useToast() {
  const toasts = useState<Toast[]>('toasts', () => [])

  function dismiss(id: string): void {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function add(type: ToastType, message: string): string {
    const id = generateId()
    const toast: Toast = { id, type, message }

    // Limite la file à MAX_TOASTS — pousse le plus ancien dehors.
    const next = [...toasts.value, toast]
    toasts.value = next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next

    // Auto-dismiss
    if (import.meta.client) {
      setTimeout(() => dismiss(id), TOAST_TTL_MS)
    }

    return id
  }

  const push = {
    success: (message: string): string => add('success', message),
    error: (message: string): string => add('error', message),
    info: (message: string): string => add('info', message),
  }

  return { toasts, push, dismiss }
}
