/**
 * Helpers numéro de téléphone — KALGA Frontend.
 * Référence : dashboard/static/app.js (normalisation à la connexion marchand).
 */

/**
 * Construit un numéro international (chiffres uniquement) à partir d'un
 * indicatif pays et d'un numéro local saisi.
 *
 * Retire le `0` de tête du numéro local (format national) : l'international le
 * supprime. Ex : CI « 05 44 21 01 12 » + indicatif « 225 » → « 225544210112 ».
 * Sans ce retrait, le marchand est introuvable en base (225 + 0544… ≠ 225544…).
 */
export function buildInternationalPhone(countryCode: string, localNumber: string): string {
  const local = localNumber.replace(/\D/g, '').replace(/^0+/, '')
  return `${countryCode}${local}`
}
