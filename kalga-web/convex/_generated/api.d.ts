/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as admin from "../admin.js";
import type * as auth from "../auth.js";
import type * as conversations from "../conversations.js";
import type * as dashboard from "../dashboard.js";
import type * as http from "../http.js";
import type * as internal_activation from "../internal/activation.js";
import type * as internal_billing from "../internal/billing.js";
import type * as internal_catalog from "../internal/catalog.js";
import type * as internal_category from "../internal/category.js";
import type * as internal_chat from "../internal/chat.js";
import type * as internal_clienthistory from "../internal/clienthistory.js";
import type * as internal_conversation from "../internal/conversation.js";
import type * as internal_followups from "../internal/followups.js";
import type * as internal_guard from "../internal/guard.js";
import type * as internal_inventory from "../internal/inventory.js";
import type * as internal_knowledge from "../internal/knowledge.js";
import type * as internal_memory from "../internal/memory.js";
import type * as internal_merchant from "../internal/merchant.js";
import type * as internal_stats from "../internal/stats.js";
import type * as internal_stockjournal from "../internal/stockjournal.js";
import type * as internal_storefront from "../internal/storefront.js";
import type * as internal_waitlist from "../internal/waitlist.js";
import type * as lib_withOrg from "../lib/withOrg.js";
import type * as merchants from "../merchants.js";
import type * as products from "../products.js";
import type * as seed from "../seed.js";
import type * as settings from "../settings.js";
import type * as storefront from "../storefront.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  admin: typeof admin;
  auth: typeof auth;
  conversations: typeof conversations;
  dashboard: typeof dashboard;
  http: typeof http;
  "internal/activation": typeof internal_activation;
  "internal/billing": typeof internal_billing;
  "internal/catalog": typeof internal_catalog;
  "internal/category": typeof internal_category;
  "internal/chat": typeof internal_chat;
  "internal/clienthistory": typeof internal_clienthistory;
  "internal/conversation": typeof internal_conversation;
  "internal/followups": typeof internal_followups;
  "internal/guard": typeof internal_guard;
  "internal/inventory": typeof internal_inventory;
  "internal/knowledge": typeof internal_knowledge;
  "internal/memory": typeof internal_memory;
  "internal/merchant": typeof internal_merchant;
  "internal/stats": typeof internal_stats;
  "internal/stockjournal": typeof internal_stockjournal;
  "internal/storefront": typeof internal_storefront;
  "internal/waitlist": typeof internal_waitlist;
  "lib/withOrg": typeof lib_withOrg;
  merchants: typeof merchants;
  products: typeof products;
  seed: typeof seed;
  settings: typeof settings;
  storefront: typeof storefront;
}>;

/**
 * A utility for referencing Convex functions in your app's public API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;

/**
 * A utility for referencing Convex functions in your app's internal API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = internal.myModule.myFunction;
 * ```
 */
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;

export declare const components: {
  betterAuth: import("../betterAuth/_generated/component.js").ComponentApi<"betterAuth">;
};
