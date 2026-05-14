import { create } from "zustand";
import type { Agent, Incident, A2AMsg } from "@/lib/api";

interface A2AEvent {
  id: string;
  from: string;
  to: string;
  type: string;
  domain: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

interface ErayaStore {
  // Agents
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  updateAgent: (agentId: string, patch: Partial<Agent>) => void;

  // A2A stream (capped at 200 events)
  a2aFeed: A2AEvent[];
  pushA2AEvent: (event: A2AEvent) => void;

  // Incidents
  openIncidents: Incident[];
  setOpenIncidents: (incidents: Incident[]) => void;
  addIncident: (incident: Incident) => void;

  // Active domain for domain-specific views
  activeDomain: string;
  setActiveDomain: (domain: string) => void;

  // Guardian alerts (for notification badge)
  guardianAlerts: number;
  incrementGuardianAlerts: () => void;
  resetGuardianAlerts: () => void;

  // Connection state
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
}

export const useErayaStore = create<ErayaStore>((set) => ({
  agents: [],
  setAgents: (agents) => set({ agents }),
  updateAgent: (agentId, patch) =>
    set((s) => ({
      agents: s.agents.map((a) => (a.agent_id === agentId ? { ...a, ...patch } : a)),
    })),

  a2aFeed: [],
  pushA2AEvent: (event) =>
    set((s) => ({
      a2aFeed: [event, ...s.a2aFeed].slice(0, 200),
    })),

  openIncidents: [],
  setOpenIncidents: (incidents) => set({ openIncidents: incidents }),
  addIncident: (incident) =>
    set((s) => ({ openIncidents: [incident, ...s.openIncidents] })),

  activeDomain: "5g",
  setActiveDomain: (domain) => set({ activeDomain: domain }),

  guardianAlerts: 0,
  incrementGuardianAlerts: () => set((s) => ({ guardianAlerts: s.guardianAlerts + 1 })),
  resetGuardianAlerts: () => set({ guardianAlerts: 0 }),

  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
