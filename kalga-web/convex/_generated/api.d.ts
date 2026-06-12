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
import type * as internal_chat from "../internal/chat.js";
import type * as internal_followups from "../internal/followups.js";
import type * as internal_guard from "../internal/guard.js";
import type * as internal_inventory from "../internal/inventory.js";
import type * as internal_memory from "../internal/memory.js";
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
  "internal/chat": typeof internal_chat;
  "internal/followups": typeof internal_followups;
  "internal/guard": typeof internal_guard;
  "internal/inventory": typeof internal_inventory;
  "internal/memory": typeof internal_memory;
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
