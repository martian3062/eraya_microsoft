import { create } from "zustand";

export interface HealthCheck {
  id: string;
  timestamp: string;
  interval: "30s" | "60s";
  domain: string;
  checker: string;
  target: string;
  status: "ok" | "warning" | "healed";
  detail: string;
  latency_ms: number;
}

interface HealthStore {
  checks: HealthCheck[];
  pushCheck: (check: HealthCheck) => void;
  clearChecks: () => void;
}

export const useHealthStore = create<HealthStore>((set) => ({
  checks: [],
  pushCheck: (check) =>
    set((s) => ({ checks: [check, ...s.checks].slice(0, 200) })),
  clearChecks: () => set({ checks: [] }),
}));
