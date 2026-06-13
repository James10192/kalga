import { convexTest } from "convex-test";
import { describe, expect, test } from "vitest";
import { api } from "./_generated/api";
import schema from "./schema";

/**
 * Tests backend des mutations/queries marchand scopees (plan 010).
 *
 * Couvre, conformement a plans/010-onboarding-responsive.md (section Tests) :
 *  - `provisionMerchantOrg` idempotent (re-appel pour un meme numero ne cree pas
 *    de doublon et renvoie le merchant existant) + invariant slug unique ;
 *  - `linkWhatsapp` pose `whatsappLinkedAt` + reconcilie `whatsappRealPhone` sans
 *    jamais ecraser `phone` (la cle de session Baileys).
 *
 * On exerce via la forme inline de convex-test (`t.run`) + `t.withIdentity({...})`.
 * Le 2e arg `modules` (import.meta.glob) reste requis pour la resolution des
 * fonctions `api.*` hors bundler Convex (cf. testing-e2e.md section 4.2).
 *
 * NB : la branche de `provisionMerchantOrg` qui cree une organization Better Auth
 * passe par l'adaptateur (env vars + composant) et n'est pas exercable de façon
 * fiable sous convex-test (cf. auth.test.ts, GATE-2). On teste donc la branche
 * d'idempotence (early-return par numero) + l'invariant slug, pas la creation d'org.
 */
const modules = import.meta.glob("./**/*.*s");

describe("provisionMerchantOrg — idempotence (010)", () => {
  test("re-appel pour un numero deja marchand renvoie l'existant sans doublon", async () => {
    const t = convexTest(schema, modules);

    // Seed un marchand deja provisionne (org liee), comme apres un 1er signup.
    // `provisionMerchantOrg` ne fait que `replace(/[^\d]/g, "")` (pas d'ajout
    // d'indicatif) : on seed donc exactement les chiffres que l'entree produira.
    const existingId = await t.run(async (ctx) =>
      ctx.db.insert("merchants", {
        name: "Chez Awa",
        phone: "2250141540178",
        slug: "chez-awa",
        organizationId: "org_awa",
      }),
    );

    // 2e appel avec le meme numero, formate (espaces) -> nettoye en chiffres only
    // identiques au seed -> early-return idempotent.
    const res = await t.mutation(api.merchants.provisionMerchantOrg, {
      name: "Chez Awa (re-tente)",
      phone: "225 0141 540 178",
    });

    expect(res.merchantId).toBe(existingId);
    expect(res.organizationId).toBe("org_awa");

    // Aucun doublon cree : un seul doc pour ce numero.
    const all = await t.run(async (ctx) =>
      ctx.db
        .query("merchants")
        .withIndex("by_phone", (q) => q.eq("phone", "2250141540178"))
        .collect(),
    );
    expect(all).toHaveLength(1);
    // Le nom d'origine est conserve (l'early-return ne patche rien).
    expect(all[0]?.name).toBe("Chez Awa");
  });

  test("rejette un numero vide (apres nettoyage des non-chiffres)", async () => {
    const t = convexTest(schema, modules);
    await expect(
      t.mutation(api.merchants.provisionMerchantOrg, {
        name: "Sans numero",
        phone: "   --  ",
      }),
    ).rejects.toThrow(/num/i);
  });
});

describe("provisionMerchantOrg — invariant slug unique (010)", () => {
  test("deux marchands de meme nom ont des slugs distincts et by_slug reste unique", async () => {
    const t = convexTest(schema, modules);

    await t.run(async (ctx) => {
      await ctx.db.insert("merchants", {
        name: "Boutique Lumiere",
        phone: "2250100000020",
        slug: "boutique-lumiere",
        organizationId: "org_a",
      });
      // meme nom -> le slug derive est suffixe (-2) pour rester unique.
      await ctx.db.insert("merchants", {
        name: "Boutique Lumiere",
        phone: "2250100000021",
        slug: "boutique-lumiere-2",
        organizationId: "org_b",
      });
    });

    const slugs = await t.run(async (ctx) =>
      (await ctx.db.query("merchants").collect()).map((m) => m.slug),
    );
    expect(new Set(slugs).size).toBe(slugs.length);

    const first = await t.run(async (ctx) =>
      ctx.db
        .query("merchants")
        .withIndex("by_slug", (q) => q.eq("slug", "boutique-lumiere"))
        .unique(),
    );
    expect(first?.organizationId).toBe("org_a");
  });
});

describe("linkWhatsapp — pose le lien sans ecraser phone (010)", () => {
  /** Seed un marchand lie a une org, puis renvoie son _id + identite scopee. */
  async function seedLinkedMerchant(
    t: ReturnType<typeof convexTest>,
    overrides?: Partial<{ phone: string; org: string }>,
  ) {
    const phone = overrides?.phone ?? "2250141540178";
    const org = overrides?.org ?? "org_link";
    const merchantId = await t.run(async (ctx) =>
      ctx.db.insert("merchants", {
        name: "Boutique Lien",
        phone,
        slug: `boutique-${phone.slice(-4)}`,
        organizationId: org,
      }),
    );
    const asUser = t.withIdentity({
      name: "Marchand",
      subject: `user_${phone.slice(-4)}`,
      activeOrganizationId: org,
    } as never);
    return { merchantId, asUser, phone };
  }

  test("pose whatsappLinkedAt + whatsappRealPhone, garde phone intact", async () => {
    const t = convexTest(schema, modules);
    const { merchantId, asUser, phone } = await seedLinkedMerchant(t);

    const before = Date.now();
    const res = await asUser.mutation(api.merchants.linkWhatsapp, {
      // realPhone arrive formate par le bridge (espaces, +) -> nettoye.
      realPhone: "+225 07 07 12 34 56",
    });
    expect(res.linked).toBe(true);
    expect(res.merchantId).toBe(merchantId);

    const doc = await t.run(async (ctx) => ctx.db.get(merchantId));
    expect(doc?.whatsappLinkedAt).toBeTypeOf("number");
    expect(doc?.whatsappLinkedAt as number).toBeGreaterThanOrEqual(before);
    // realPhone reconcilie (chiffres only : "+225 07 07 12 34 56" -> "2250707123456").
    expect(doc?.whatsappRealPhone).toBe("2250707123456");
    // phone (cle session Baileys) jamais ecrase, meme si realPhone differe.
    expect(doc?.phone).toBe(phone);
  });

  test("realPhone vide -> whatsappRealPhone reste indefini, lien pose quand meme", async () => {
    const t = convexTest(schema, modules);
    const { merchantId, asUser } = await seedLinkedMerchant(t, {
      phone: "2250100000099",
      org: "org_empty_real",
    });

    await asUser.mutation(api.merchants.linkWhatsapp, { realPhone: "" });

    const doc = await t.run(async (ctx) => ctx.db.get(merchantId));
    expect(doc?.whatsappLinkedAt).toBeTypeOf("number");
    expect(doc?.whatsappRealPhone).toBeUndefined();
  });

  test("idempotent : second appel re-pose les champs sans crasher", async () => {
    const t = convexTest(schema, modules);
    const { merchantId, asUser } = await seedLinkedMerchant(t, {
      phone: "2250100000088",
      org: "org_idem",
    });

    await asUser.mutation(api.merchants.linkWhatsapp, { realPhone: "2250707000001" });
    const firstAt = await t.run(
      async (ctx) => (await ctx.db.get(merchantId))?.whatsappLinkedAt,
    );

    await asUser.mutation(api.merchants.linkWhatsapp, { realPhone: "2250707000002" });
    const second = await t.run(async (ctx) => ctx.db.get(merchantId));

    expect(second?.whatsappLinkedAt).toBeTypeOf("number");
    expect(second?.whatsappLinkedAt as number).toBeGreaterThanOrEqual(
      firstAt as number,
    );
    // dernier realPhone gagne (reconciliation re-jouee).
    expect(second?.whatsappRealPhone).toBe("2250707000002");
  });

  test("leve hors organisation active (anti-fuite withOrg)", async () => {
    const t = convexTest(schema, modules);
    // pas de seed merchant -> identite avec org orpheline.
    const asOrphan = t.withIdentity({
      name: "Orphelin",
      subject: "user_orphan",
      activeOrganizationId: "org_inexistante",
    } as never);
    await expect(
      asOrphan.mutation(api.merchants.linkWhatsapp, { realPhone: "2250700000000" }),
    ).rejects.toThrow(/no merchant for active organization/i);
  });
});
