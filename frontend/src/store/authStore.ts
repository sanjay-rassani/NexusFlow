/**
 * Zustand auth store — single source of truth for user identity and session.
 *
 * On app mount, if tokens are in localStorage, the store tries to fetch /auth/me/
 * to hydrate the user object. If that fails, tokens are cleared.
 */

import { create } from "zustand";
import type { User } from "../api/auth";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,          // true until initial /me/ fetch resolves
  isAuthenticated: false,

  setUser: (user) =>
    set({ user, isAuthenticated: user !== null, isLoading: false }),

  setLoading: (isLoading) => set({ isLoading }),

  reset: () =>
    set({ user: null, isAuthenticated: false, isLoading: false }),
}));
