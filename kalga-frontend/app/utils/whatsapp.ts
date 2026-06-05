/**
 * Helpers WhatsApp deep links — wa.me protocol.
 * Référence : ARCHITECTURE_FRONTEND.md section 4 (utils/)
 *
 * Format officiel : https://wa.me/<phone>?text=<url-encoded-text>
 * - `phone` doit être en chiffres uniquement (sans + ni espaces)
 * - `text` doit être URL-encoded (encodeURIComponent)
 */

/**
 * Construit un lien wa.me sécurisé.
 *
 * @param phone Numéro international en chiffres (ex: "2250161407534")
 * @param text  Message pré-rempli (sera URL-encodé)
 */
export function buildWhatsAppLink(phone: string, text?: string): string {
  const cleanPhone = phone.replace(/\D/g, '')
  if (!cleanPhone) return '#'
  const base = `https://wa.me/${cleanPhone}`
  if (!text) return base
  return `${base}?text=${encodeURIComponent(text)}`
}
