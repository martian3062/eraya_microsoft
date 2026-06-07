"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type UserRole = "operator" | "guest";

export interface AuthUser {
  name: string;
  role: UserRole;
  image?: string;   // Google profile picture
  email?: string;
}

interface AuthStore {
  user: AuthUser | null;
  login: (user: AuthUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      login: (user) => set({ user }),
      logout: () => set({ user: null }),
    }),
    { name: "eraya-auth" }
  )
);
