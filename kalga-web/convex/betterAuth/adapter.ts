import { createApi } from "@convex-dev/better-auth";
import schema from "./schema";
import { createAuthOptions } from "../auth";

// Fonctions adapter du composant LOCAL (CRUD sur les tables Better Auth).
// Generees a partir du schema local + des options auth (plugins).
export const {
  create,
  findOne,
  findMany,
  updateOne,
  updateMany,
  deleteOne,
  deleteMany,
} = createApi(schema, createAuthOptions);
