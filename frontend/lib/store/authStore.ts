"use client";

import { create } from "zustand";
import { api, clearCartToken } from "@/lib/api/client";
import type {
  AuthUserResponse,
  CurrentUser,
  DetailResponse,
  LoginRequest,
  RegisterRequest,
  RegisterResponse,
  Session,
} from "@/lib/api/types";

/**
 * Who is signed in.
 *
 * Deliberately **not** persisted to localStorage. The session cookie is the
 * truth; a cached copy would keep showing someone as signed in after their
 * session expired or they signed out in another tab.
 */
export type AuthStatus = "idle" | "loading" | "authenticated" | "anonymous";

interface AuthStore {
  user: CurrentUser | null;
  status: AuthStatus;
  /** Ask the backend who this is. Safe to call repeatedly; runs once. */
  bootstrap: () => Promise<void>;
  /** Re-read the session, e.g. after returning from a social provider. */
  refresh: () => Promise<void>;
  login: (credentials: LoginRequest) => Promise<CurrentUser>;
  /**
   * Create an account. Email verification is mandatory, so this does **not**
   * sign the customer in — they are signed in by following the emailed link.
   */
  register: (payload: RegisterRequest) => Promise<RegisterResponse>;
  /** Confirm an email address from the emailed key. Signs the customer in. */
  verifyEmail: (key: string) => Promise<CurrentUser>;
  resendVerification: (email: string) => Promise<DetailResponse>;
  requestPasswordReset: (email: string) => Promise<DetailResponse>;
  confirmPasswordReset: (payload: { uid: string; token: string; new_password: string }) => Promise<DetailResponse>;
  logout: () => Promise<void>;
  /** The server has already ended the session (e.g. the account was erased). */
  endSession: () => void;
}

export const useAuthStore = create<AuthStore>()((set, get) => ({
  user: null,
  status: "idle",

  bootstrap: async () => {
    if (get().status !== "idle") return;
    await get().refresh();
  },

  refresh: async () => {
    set({ status: "loading" });
    try {
      const session = await api<Session>("/auth/session/");
      set({ user: session.user, status: session.user ? "authenticated" : "anonymous" });
    } catch {
      // An unreachable API must not leave the UI stuck on a spinner. Treat it
      // as signed out; protected screens surface their own errors.
      set({ user: null, status: "anonymous" });
    }
  },

  login: async (credentials) => {
    const { user } = await api<AuthUserResponse>("/auth/login/", { method: "POST", body: credentials });
    set({ user, status: "authenticated" });
    return user;
  },

  register: (payload) => api<RegisterResponse>("/auth/register/", { method: "POST", body: payload }),

  verifyEmail: async (key) => {
    const { user } = await api<AuthUserResponse>("/auth/verify-email/", { method: "POST", body: { key } });
    set({ user, status: "authenticated" });
    return user;
  },

  resendVerification: (email) =>
    api<DetailResponse>("/auth/resend-verification/", { method: "POST", body: { email } }),

  requestPasswordReset: (email) =>
    api<DetailResponse>("/auth/password/reset/", { method: "POST", body: { email } }),

  confirmPasswordReset: (payload) =>
    api<DetailResponse>("/auth/password/reset/confirm/", { method: "POST", body: payload }),

  logout: async () => {
    try {
      await api<void>("/auth/logout/", { method: "POST" });
    } finally {
      // Signed out locally even if the request failed: leaving the UI signed in
      // after the customer asked to leave is the worse failure. The cart token
      // goes too, so the next visitor on this device starts a fresh cart.
      clearCartToken();
      set({ user: null, status: "anonymous" });
    }
  },

  endSession: () => {
    clearCartToken();
    set({ user: null, status: "anonymous" });
  },
}));
