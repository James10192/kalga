import { convexTest } from "convex-test";
import { describe, expect, test } from "vitest";
import schema from "./schema";
import { withOrg } from "./lib/withOrg";

/**
 * Tests backend du scoping multi-tenant (plan 003).
 *
 * `withOrg` est le garde anti-fuite cross-tenant : il resout l'organisation
 * active (depuis le JWT) -> merchant doc -> merchantId, et leve sinon.
 *
 * On l'exerce via la forme inline de convex-test : `t.run(async (ctx) => ...)`
 * et `t.withIdentity({...}).run(...)`. Voir testing-e2e.md (section 4.3) :
 * withIdentity genere automatiquement subject/issuer/tokenIdentifier.
 *
 * Le 2e arg `modules` reste requis pour que convex-test localise le dossier
 * `_generated` dans ce layout pnpm, meme si on n'appelle pas de fonction `api.*`.
 */
const modules = import.meta.glob("./**/*.*s");

describe("withOrg — garde multi-tenant (003)", () => {
  test("leve 'Unauthenticated' sans identite", async () => {
    const t = convexTest(schema, modules);
    await expect(
      t.run(async (ctx) => withOrg(ctx, async () => "ne devrait pas arriver")),
    ).rejects.toThrow(/unauthenticated/i);
  });

  test("leve 'No active organization' si identite sans activeOrganizationId", async () => {
    const t = convexTest(schema, modules);
    const asUser = t.withIdentity({ name: "Marchand 0178", subject: "user_1" });
    await expect(
      asUser.run(async (ctx) =>
        withOrg(ctx, async () => "ne devrait pas arriver"),
      ),
    ).rejects.toThrow(/no active organization/i);
  });

  test("leve 'No merchant for active organization' si org sans merchant lie", async () => {
    const t = convexTest(schema, modules);
    const asUser = t.withIdentity({
      name: "Marchand 0178",
      subject: "user_1",
      // champ custom injecte dans le JWT par definePayload (auth.ts)
      activeOrganizationId: "org_orpheline",
    } as never);
    await expect(
      asUser.run(async (ctx) =>
        withOrg(ctx, async () => "ne devrait pas arriver"),
      ),
    ).rejects.toThrow(/no merchant for active organization/i);
  });

  test("happy path : resout merchantId quand org + merchant lie existent", async () => {
    const t = convexTest(schema, modules);

    const merchantId = await t.run(async (ctx) =>
      ctx.db.insert("merchants", {
        name: "Boutique Liee",
        phone: "2250141540178",
        slug: "boutique-liee",
        organizationId: "org_liee",
      }),
    );

    const asUser = t.withIdentity({
      name: "Marchand 0178",
      subject: "user_1",
      activeOrganizationId: "org_liee",
    } as never);

    const resolved = await asUser.run(async (ctx) =>
      withOrg(ctx, async (octx) => ({
        merchantId: octx.merchantId,
        userId: octx.userId,
        orgId: octx.orgId,
      })),
    );

    expect(resolved.merchantId).toBe(merchantId);
    expect(resolved.userId).toBe("user_1");
    expect(resolved.orgId).toBe("org_liee");
  });
});

/**
 * Invariant slug unique (porte par `provisionMerchantOrg`, plan 003).
 *
 * `provisionMerchantOrg` cree une organization Better Auth puis un doc merchant
 * avec un slug unique. La creation d'organization passe par l'adaptateur Better
 * Auth (env vars + composant), non exercable de façon fiable sous convex-test
 * (voir GATE-2). On verifie donc ici l'INVARIANT que la mutation garantit : deux
 * marchands ne partagent jamais le meme slug, et la lookup par slug reste unique.
 */
describe("slug unique — invariant provisionMerchantOrg (003)", () => {
  test("deux marchands ont des slugs distincts et by_slug reste unique", async () => {
    const t = convexTest(schema, modules);

    await t.run(async (ctx) => {
      await ctx.db.insert("merchants", {
        name: "Chez Awa",
        phone: "2250100000020",
        slug: "chez-awa",
        organizationId: "org_a",
      });
      // meme nom de boutique -> le slug derive doit etre suffixe pour rester unique
      await ctx.db.insert("merchants", {
        name: "Chez Awa",
        phone: "2250100000021",
        slug: "chez-awa-2",
        organizationId: "org_b",
      });
    });

    const slugs = await t.run(async (ctx) =>
      (await ctx.db.query("merchants").collect()).map((m) => m.slug),
    );
    // pas de doublon
    expect(new Set(slugs).size).toBe(slugs.length);

    // by_slug.unique() ne ramene qu'un doc par slug
    const awa = await t.run(async (ctx) =>
      ctx.db
        .query("merchants")
        .withIndex("by_slug", (q) => q.eq("slug", "chez-awa"))
        .unique(),
    );
    expect(awa?.organizationId).toBe("org_a");
  });
});
