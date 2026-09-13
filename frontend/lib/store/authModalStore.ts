"use client";

import { create } from "zustand";

export type AuthView = "login" | "signup" | "forgot";

/**
 * Whether the sign-in dialog is showing, and where to go afterwards.
 *
 * Separate from `authStore` because this is UI state, not session state: any
 * screen can ask for sign-in without knowing who mounts the dialog.
 */
interface AuthModalStore {
  isOpen: boolean;
  view: AuthView;
  /** A safe relative path to visit once signed in, or null to stay put. */
  next: string | null;
  open: (view?: AuthView, next?: string | null) => void;
  setView: (view: AuthView) => void;
  close: () => void;
}

export const useAuthModalStore = create<AuthModalStore>()((set) => ({
  isOpen: false,
  view: "login",
  next: null,
  open: (view = "login", next = null) => set({ isOpen: true, view, next }),
  setView: (view) => set({ view }),
  close: () => set({ isOpen: false, next: null }),
}));
