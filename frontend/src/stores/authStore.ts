"use client";

import { create } from "zustand";
import * as api from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: typeof window !== "undefined" ? api.getStoredUser() : null,
  token: typeof window !== "undefined" ? api.getToken() : null,

  async login(email, password) {
    const session = await api.login(email, password);
    api.storeSession(session);
    set({ user: session.user, token: session.access_token });
  },

  logout() {
    api.clearSession();
    set({ user: null, token: null });
  },
}));