import type { GenericMutationCtx, GenericQueryCtx } from "convex/server";
import type { DataModel, Id } from "../_generated/dataModel";

type AnyCtx = GenericQueryCtx<DataModel> | GenericMutationCtx<DataModel>;

export type OrgContext<Ctx> = Ctx & {
  /** organization.id Better Auth (= merchant.organizationId). */
  orgId: string;
  /** userId Better Auth (identity.subject). */
  userId: string;
  /** role (admin/user/owner...). */
  role: string;
  /** doc merchant lie a l'org active. */
  merchantId: Id<"merchants">;
};

/**
 * Resout l'organisation active (depuis le JWT) -> merchant doc -> merchantId.
 * Toute query/mutation metier DOIT passer par ici (anti-fuite cross-tenant).
 * Leve si non authentifie, sans org active, ou sans merchant lie a l'org.
 */
export async function withOrg<Ctx extends AnyCtx, T>(
  ctx: Ctx,
  fn: (octx: OrgContext<Ctx>) => Promise<T>,
): Promise<T> {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Unauthenticated");

  const orgId = (identity as { activeOrganizationId?: string }).activeOrganizationId;
  if (!orgId) throw new Error("No active organization");

  const merchant = await ctx.db
    .query("merchants")
    .withIndex("by_organization", (q) => q.eq("organizationId", orgId))
    .unique();
  if (!merchant) throw new Error("No merchant for active organization");

  return fn({
    ...ctx,
    orgId,
    userId: identity.subject,
    role: (identity as { role?: string }).role ?? "user",
    merchantId: merchant._id,
  } as OrgContext<Ctx>);
}
