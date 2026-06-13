import { convexTest } from "convex-test";
import { describe, expect, test } from "vitest";
import { api } from "./_generated/api";
import type { Id } from "./_generated/dataModel";
import schema from "./schema";

/**
 * Tests backend de l'isolation multi-tenant des queries dashboard (plan 010).
 *
 * Garde anti-fuite : les variantes `feed`, `todaySummary`, `salesRegistry`
 * resolvent le marchand via `withOrg` (organisation active du JWT), sans aucun
 * `merchantId` venant du client. On verifie qu'une query jouee comme org A ne
 * voit JAMAIS la donnee de l'org B, et reciproquement.
 *
 * Le 2e arg `modules` (import.meta.glob) reste requis pour la resolution des
 * fonctions `api.*` hors bundler Convex (cf. testing-e2e.md section 4.2).
 */
const modules = import.meta.glob("./**/*.*s");

type Seeded = {
  mA: Id<"merchants">;
  mB: Id<"merchants">;
  asA: ReturnType<ReturnType<typeof convexTest>["withIdentity"]>;
  asB: ReturnType<ReturnType<typeof convexTest>["withIdentity"]>;
};

/**
 * Seed deux marchands (A, B) lies a deux organisations distinctes, chacun avec
 * un produit + une conversation `completed` portant un montant (offre courante).
 * Renvoie aussi les identites scopees correspondantes.
 */
async function seedTwoTenants(t: ReturnType<typeof convexTest>): Promise<Seeded> {
  const { mA, mB } = await t.run(async (ctx) => {
    const mA = await ctx.db.insert("merchants", {
      name: "Marchand A",
      phone: "2250100000001",
      slug: "marchand-a",
      organizationId: "org_a",
    });
    const mB = await ctx.db.insert("merchants", {
      name: "Marchand B",
      phone: "2250100000002",
      slug: "marchand-b",
      organizationId: "org_b",
    });

    const pA = await ctx.db.insert("products", {
      merchantId: mA,
      name: "Sac A",
      code: "A1",
      price: 15000,
      minPrice: 12000,
    });
    const pB = await ctx.db.insert("products", {
      merchantId: mB,
      name: "Robe B",
      code: "B1",
      price: 20000,
      minPrice: 16000,
    });

    const now = Date.now();
    const cA = await ctx.db.insert("conversations", {
      merchantId: mA,
      productId: pA,
      clientPhone: "2250500000001",
      status: "completed",
      currentOffer: 14000,
      updatedAt: now,
    });
    const cB = await ctx.db.insert("conversations", {
      merchantId: mB,
      productId: pB,
      clientPhone: "2250500000002",
      status: "completed",
      currentOffer: 19000,
      updatedAt: now,
    });

    await ctx.db.insert("messages", {
      conversationId: cA,
      content: "Bonjour, je prends le sac A",
      isFromClient: true,
    });
    await ctx.db.insert("messages", {
      conversationId: cB,
      content: "Je veux la robe B",
      isFromClient: true,
    });

    return { mA, mB };
  });

  const asA = t.withIdentity({
    name: "A",
    subject: "user_a",
    activeOrganizationId: "org_a",
  } as never);
  const asB = t.withIdentity({
    name: "B",
    subject: "user_b",
    activeOrganizationId: "org_b",
  } as never);

  return { mA, mB, asA, asB };
}

describe("dashboard withOrg — isolation cross-tenant (010)", () => {
  test("feed ne renvoie que les conversations de l'org courante", async () => {
    const t = convexTest(schema, modules);
    const { mA, mB, asA, asB } = await seedTwoTenants(t);

    const feedA = await asA.query(api.dashboard.feed, {});
    expect(feedA).toHaveLength(1);
    expect(feedA[0]?.clientPhone).toBe("2250500000001");
    expect(feedA[0]?.productName).toBe("Sac A");
    // aucune fuite : pas de conversation/produit de B.
    expect(feedA.some((c) => c.productName === "Robe B")).toBe(false);

    const feedB = await asB.query(api.dashboard.feed, {});
    expect(feedB).toHaveLength(1);
    expect(feedB[0]?.clientPhone).toBe("2250500000002");
    expect(feedB[0]?.productName).toBe("Robe B");

    // garde-fou : les deux ensembles sont disjoints.
    void mA;
    void mB;
  });

  test("todaySummary chiffre uniquement les ventes de l'org courante", async () => {
    const t = convexTest(schema, modules);
    const { asA, asB } = await seedTwoTenants(t);

    const sumA = await asA.query(api.dashboard.todaySummary, {});
    const sumB = await asB.query(api.dashboard.todaySummary, {});

    // A vend 14000 (offre courante), B vend 19000 : aucune contamination.
    expect(sumA.todayRevenue).toBe(14000);
    expect(sumA.todaySales).toBe(1);
    expect(sumB.todayRevenue).toBe(19000);
    expect(sumB.todaySales).toBe(1);
  });

  test("salesRegistry n'expose que les ventes de l'org courante", async () => {
    const t = convexTest(schema, modules);
    const { asA, asB } = await seedTwoTenants(t);

    const regA = await asA.query(api.dashboard.salesRegistry, {});
    expect(regA.sales).toHaveLength(1);
    expect(regA.sales[0]?.amount).toBe(14000);
    expect(regA.sales[0]?.productName).toBe("Sac A");
    expect(regA.todayTotal).toBe(14000);
    // aucune vente de B dans le registre de A.
    expect(regA.sales.some((s) => s.productName === "Robe B")).toBe(false);

    const regB = await asB.query(api.dashboard.salesRegistry, {});
    expect(regB.sales).toHaveLength(1);
    expect(regB.sales[0]?.amount).toBe(19000);
    expect(regB.sales[0]?.productName).toBe("Robe B");
  });

  test("les queries withOrg levent sans organisation active", async () => {
    const t = convexTest(schema, modules);
    await seedTwoTenants(t);

    const asNoOrg = t.withIdentity({ name: "X", subject: "user_x" });
    await expect(asNoOrg.query(api.dashboard.feed, {})).rejects.toThrow(
      /no active organization/i,
    );
    await expect(
      asNoOrg.query(api.dashboard.todaySummary, {}),
    ).rejects.toThrow(/no active organization/i);
    await expect(
      asNoOrg.query(api.dashboard.salesRegistry, {}),
    ).rejects.toThrow(/no active organization/i);
  });
});
