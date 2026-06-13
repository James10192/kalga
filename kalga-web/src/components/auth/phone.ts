/**
 * Aides numero de telephone (Cote d'Ivoire, indicatif +225).
 *
 * Le compte est identifie par les chiffres avec indicatif pays, ex
 * `225XXXXXXXXXX`. Better Auth recoit un email derive `{digits}@kalga.local`
 * (cache, jamais affiche). On normalise ce que l'utilisateur saisit.
 */

/** Indicatif pays Cote d'Ivoire (sans `+`). */
export const COUNTRY_CODE = "225"

/** Ne garde que les chiffres d'une chaine. */
export function onlyDigits(input: string): string {
  return input.replace(/\D/g, "")
}

/**
 * Construit le numero canonique stocke (indicatif + numero local), ex
 * entree `07 41 54 01 78` -> `2250741540178`. Tolere :
 *  - un `0` initial du format local ivoirien (on le retire),
 *  - un indicatif `225` deja saisi (on ne le double pas).
 * Renvoie `""` si la partie locale est vide.
 */
export function toCanonicalPhone(localInput: string): string {
  let digits = onlyDigits(localInput)
  if (!digits) return ""
  // Indicatif deja present en tete : on le retire pour repartir du local.
  if (digits.startsWith(COUNTRY_CODE)) {
    digits = digits.slice(COUNTRY_CODE.length)
  }
  // Format local ivoirien parfois saisi avec un 0 initial.
  if (digits.startsWith("0")) {
    digits = digits.replace(/^0+/, "")
  }
  if (!digits) return ""
  return COUNTRY_CODE + digits
}

/** Partie locale (sans indicatif) a partir d'une saisie quelconque. */
export function localPart(input: string): string {
  const canonical = toCanonicalPhone(input)
  return canonical ? canonical.slice(COUNTRY_CODE.length) : ""
}

/** Numero de la session bridge -> format affichable `+225 07 41 54 01 78`. */
export function formatDisplayPhone(canonical: string): string {
  const local = canonical.startsWith(COUNTRY_CODE)
    ? canonical.slice(COUNTRY_CODE.length)
    : canonical
  const padded = local.length === 9 ? "0" + local : local
  const groups = padded.match(/.{1,2}/g) ?? [padded]
  return `+${COUNTRY_CODE} ${groups.join(" ")}`
}

/**
 * Numero local ivoirien valide ? On reste tolerant (8 a 10 chiffres) pour ne pas
 * bloquer des formats reels ; l'erreur dure viendra du serveur si besoin.
 */
export function isValidLocalPhone(localInput: string): boolean {
  const local = localPart(localInput)
  return local.length >= 8 && local.length <= 10
}

/** Email cache derive du numero canonique, attendu par Better Auth. */
export function phoneToEmail(canonical: string): string {
  return `${canonical}@kalga.local`
}
