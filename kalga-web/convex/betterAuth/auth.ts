import { createAuth } from "../auth";

// Instance STATIQUE uniquement pour la generation de schema Better Auth (CLI).
// Ne RIEN ajouter d'autre dans ce fichier (sinon erreurs runtime a la generation).
export const auth = createAuth({} as never);
