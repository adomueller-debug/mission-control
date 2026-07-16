import { create } from "zustand";

import { api, API_BASE } from "./api";

export type RunStatus =
  | "queued"
  | "planning"
  | "executing"
  | "validating"
  | "publishing"
  | "completed"
  | "failed"
  | "cancelled";

export type AgentRun = {
  id: string;
  task: string;
  workspace: string;
  source_workspace: string;
  run_kind: string;
  workstream: "internal" | "project" | "standalone";
  status: RunStatus;
  current_step: string | null;
  plan: unknown;
  result: {
    summary?: string;
    files?: string[];
    findings?: string[];
    artifacts?: Array<{ title: string; content: string; artifact_type: string }>;
    next_actions?: string[];
    sources?: string[];
    validation?: unknown;
    executor?: { task_type: string; agent: string };
  } | null;
  error: string | null;
  branch: string | null;
  pr_url: string | null;
  publish: boolean;
  tool_calls: number;
  repair_attempts: number;
  limits: {
    max_tool_calls: number;
    max_repair_attempts: number;
    timeout_seconds: number;
  };
  created_at: string;
  updated_at: string;
};

export type CreateRunOptions = {
  workspace: string;
  publish: boolean;
  timeout_seconds: number;
  max_tool_calls: number;
  max_repair_attempts: number;
};

export type RunEvent = {
  id: number;
  run_id: string;
  type: string;
  payload: unknown;
  created_at: string;
};

type RunState = {
  runs: AgentRun[];
  activeRun: AgentRun | null;
  events: RunEvent[];
  loading: boolean;
  error: string | null;
  loadRuns: () => Promise<void>;
  selectRun: (id: string) => Promise<void>;
  createRun: (task: string, options: CreateRunOptions) => Promise<AgentRun>;
  cancelRun: () => Promise<void>;
  resumeRun: () => Promise<void>;
  addEvent: (event: RunEvent) => void;
  updateActive: (run: AgentRun) => void;
};

export const useRunStore = create<RunState>((set, get) => ({
  runs: [],
  activeRun: null,
  events: [],
  loading: false,
  error: null,

  async loadRuns() {
    try {
      const runs = await api<AgentRun[]>("/api/v1/runs");
      set({ runs, error: null });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Runs konnten nicht geladen werden" });
    }
  },

  async selectRun(id) {
    const [activeRun, events] = await Promise.all([
      api<AgentRun>(`/api/v1/runs/${id}`),
      api<RunEvent[]>(`/api/v1/runs/${id}/events`),
    ]);
    set({ activeRun, events, error: null });
  },

  async createRun(task, options) {
    set({ loading: true, error: null });
    try {
      const run = await api<AgentRun>("/api/v1/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task,
          workspace: options.workspace,
          options: {
            publish: options.publish,
            timeout_seconds: options.timeout_seconds,
            max_tool_calls: options.max_tool_calls,
            max_repair_attempts: options.max_repair_attempts,
          },
        }),
      });
      set((state) => ({
        runs: [run, ...state.runs],
        activeRun: run,
        events: [],
        loading: false,
      }));
      return run;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Run konnte nicht gestartet werden";
      set({ loading: false, error: message });
      throw error;
    }
  },

  async cancelRun() {
    const run = get().activeRun;
    if (!run) return;
    const activeRun = await api<AgentRun>(`/api/v1/runs/${run.id}/cancel`, { method: "POST" });
    set({ activeRun });
  },

  async resumeRun() {
    const run = get().activeRun;
    if (!run) return;
    const activeRun = await api<AgentRun>(`/api/v1/runs/${run.id}/resume`, { method: "POST" });
    set({ activeRun });
  },

  addEvent(event) {
    set((state) => ({ events: [...state.events.filter((item) => item.id !== event.id), event] }));
  },

  updateActive(activeRun) {
    set((state) => ({
      activeRun,
      runs: state.runs.map((run) => (run.id === activeRun.id ? activeRun : run)),
    }));
  },
}));

export function reportUrl(runId: string) {
  return `${API_BASE}/api/v1/runs/${runId}/report`;
}
