import { createAuthClient } from "better-auth/react";
import {
  organizationClient,
  adminClient,
  phoneNumberClient,
} from "better-auth/client/plugins";
import { convexClient } from "@convex-dev/better-auth/client/plugins";

export const authClient = createAuthClient({
  // baseURL non requis : le proxy /api/auth/* est sur la meme origine.
  plugins: [
    organizationClient(),
    adminClient(),
    phoneNumberClient(),
    convexClient(), // toujours present cote client
  ],
});

export const {
  signIn,
  signOut,
  useSession,
  organization, // organization.create, .setActive, .inviteMember, ...
  admin, // admin.impersonateUser, .listUsers, ...
  phoneNumber, // phoneNumber.sendOtp, .verify, ...
} = authClient;
