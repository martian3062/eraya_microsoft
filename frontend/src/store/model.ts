import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ModelStore {
  activeModelKey: string;
  setActiveModel: (key: string) => void;
}

export const useModelStore = create<ModelStore>()(
  persist(
    (set) => ({
      activeModelKey: "groq-llama-3.3-70b",
      setActiveModel: (key) => set({ activeModelKey: key }),
    }),
    { name: "eraya-model" }
  )
);
