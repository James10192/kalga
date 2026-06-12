import { convexTest } from "convex-test";
import { describe, expect, test } from "vitest";
import { api } from "./_generated/api";
import schema from "./schema";

/**
 * Tests backend du schema metier (plan 002).
 *
 * Couvre, conformement a plans/reference/testing-e2e.md (section 4) :
 *  - insertion de documents,
 *  - lecture via index `by_merchant` (scoping tenant),
 *  - validation des enums (un literal hors union est rejete par le validateur).
 *
 * Le 2e arg `modules` (import.meta.glob) est requis quand Vitest tourne sans le
 * bundler Convex : il permet a convex-test de retrouver les fonctions appelees
 * via `api.*`. Voir testing-e2e.md (section 4.2, piege module resolution).
 */
const modules = import.meta.glob("./**/*.*s");

describe("schema 002 — insertion + index by_merchant", () => {
  test("insere un merchant et le relit par _id", async () => {
    const t = convexTest(schema, modules);

    const merchantId = await t.run(async (ctx) =>
      ctx.db.insert("merchants", {
        name: "Boutique Test",
        phone: "2250141540178",
        slug: "boutique-test",
      }),
    );

    const doc = await t.run(async (ctx) => ctx.db.get(merchantId));
    expect(doc?.name).toBe("Boutique Test");
    expect(doc?.phone).toBe("2250141540178");
    // `_creationTime` et `_id` sont auto-injectes par Convex.
    expect(doc?._creationTime).toBeTypeOf("number");
  });

  test("listByMerchant ne renvoie que les produits du marchand (index by_merchant)", async () => {
    const t = convexTest(schema, modules);

    const { mA, mB } = await t.run(async (ctx) => {
      const mA = await ctx.db.insert("merchants", {
        name: "Marchand A",
        phone: "2250100000001",
        slug: "marchand-a",
      });
      const mB = await ctx.db.insert("merchants", {
        name: "Marchand B",
        phone: "2250100000002",
        slug: "marchand-b",
      });
      await ctx.db.insert("products", {
        merchantId: mA,
        name: "Sac A1",
        code: "A1",
        price: 15000,
        minPrice: 12000,
      });
      await ctx.db.insert("products", {
        merchantId: mA,
        name: "Sac A2",
        code: "A2",
        price: 9000,
        minPrice: 7000,
      });
      await ctx.db.insert("products", {
        merchantId: mB,
        name: "Robe B1",
        code: "B1",
        price: 20000,
        minPrice: 16000,
      });
      return { mA, mB };
    });

    const productsA = await t.query(api.products.listByMerchant, {
      merchantId: mA,
    });
    expect(productsA).toHaveLength(2);
    expect(productsA.map((p) => p.code).sort()).toEqual(["A1", "A2"]);
    // Aucune fuite cross-tenant : pas de produit du marchand B.
    expect(productsA.every((p) => p.merchantId === mA)).toBe(true);

    const productsB = await t.query(api.products.listByMerchant, {
      merchantId: mB,
    });
    expect(productsB).toHaveLength(1);
    expect(productsB[0]?.code).toBe("B1");
  });

  test("getByCode retrouve un produit par son code unique", async () => {
    const t = convexTest(schema, modules);
    await t.run(async (ctx) => {
      const m = await ctx.db.insert("merchants", {
        name: "Marchand Code",
        phone: "2250100000003",
        slug: "marchand-code",
      });
      await ctx.db.insert("products", {
        merchantId: m,
        name: "Chaussure",
        code: "SHOE-1",
        price: 30000,
        minPrice: 25000,
      });
    });

    const found = await t.query(api.products.getByCode, { code: "SHOE-1" });
    expect(found?.name).toBe("Chaussure");

    const missing = await t.query(api.products.getByCode, { code: "NOPE" });
    expect(missing).toBeNull();
  });

  test("getBySlug retrouve un marchand par son slug ({slug}.kalga.app)", async () => {
    const t = convexTest(schema, modules);
    await t.run(async (ctx) =>
      ctx.db.insert("merchants", {
        name: "Marchand Slug",
        phone: "2250100000004",
        slug: "marchand-slug",
      }),
    );

    const found = await t.query(api.merchants.getBySlug, {
      slug: "marchand-slug",
    });
    expect(found?.name).toBe("Marchand Slug");

    const missing = await t.query(api.merchants.getBySlug, {
      slug: "introuvable",
    });
    expect(missing).toBeNull();
  });
});

describe("schema 002 — enums (union de literals)", () => {
  test("conversations.status accepte un etat vivant (pending_delivery)", async () => {
    const t = convexTest(schema, modules);
    const convId = await t.run(async (ctx) => {
      const m = await ctx.db.insert("merchants", {
        name: "M",
        phone: "2250100000010",
        slug: "m-enum-ok",
      });
      const p = await ctx.db.insert("products", {
        merchantId: m,
        name: "P",
        code: "P-ENUM",
        price: 1000,
        minPrice: 800,
      });
      return ctx.db.insert("conversations", {
        merchantId: m,
        productId: p,
        clientPhone: "2250500000000",
        status: "pending_delivery",
      });
    });
    const conv = await t.run(async (ctx) => ctx.db.get(convId));
    expect(conv?.status).toBe("pending_delivery");
  });

  test("conversations.status rejette un literal hors union", async () => {
    const t = convexTest(schema, modules);
    await expect(
      t.run(async (ctx) => {
        const m = await ctx.db.insert("merchants", {
          name: "M",
          phone: "2250100000011",
          slug: "m-enum-ko",
        });
        const p = await ctx.db.insert("products", {
          merchantId: m,
          name: "P",
          code: "P-ENUM-KO",
          price: 1000,
          minPrice: 800,
        });
        return ctx.db.insert("conversations", {
          merchantId: m,
          productId: p,
          clientPhone: "2250500000001",
          // valeur invalide : pas dans l'union conversations.status
          status: "not_a_real_status" as never,
        });
      }),
    ).rejects.toThrow();
  });

  test("followUps.status rejette un literal hors union", async () => {
    const t = convexTest(schema, modules);
    await expect(
      t.run(async (ctx) => {
        const m = await ctx.db.insert("merchants", {
          name: "M",
          phone: "2250100000012",
          slug: "m-followup-ko",
        });
        const p = await ctx.db.insert("products", {
          merchantId: m,
          name: "P",
          code: "P-FU-KO",
          price: 1000,
          minPrice: 800,
        });
        const c = await ctx.db.insert("conversations", {
          merchantId: m,
          productId: p,
          clientPhone: "2250500000002",
          status: "active",
        });
        return ctx.db.insert("followUps", {
          conversationId: c,
          merchantId: m,
          clientPhone: "2250500000002",
          scheduledAt: Date.now(),
          message: "relance",
          status: "bogus" as never,
        });
      }),
    ).rejects.toThrow();
  });
});
