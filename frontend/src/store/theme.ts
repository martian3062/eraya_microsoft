"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ThemeStore {
  dark: boolean;
  toggle: () => void;
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      dark: false,
      toggle: () => set((s) => ({ dark: !s.dark })),
    }),
    { name: "eraya-theme" }
  )
);
