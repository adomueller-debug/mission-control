export type AgentStatus =
  | "offline"
  | "waiting"
  | "active"
  | "completed"
  | "skipped"
  | "blocked"
  | "paused"
  | "error";

export const AGENT_STATUS_LABELS: Record<AgentStatus, string> = {
  offline: "Offline",
  waiting: "Wartet",
  active: "Aktiv",
  completed: "Abgeschlossen",
  skipped: "Übersprungen",
  blocked: "Blockiert",
  paused: "Pausiert",
  error: "Fehler",
};

export const AGENT_STATUS_DOTS: Record<AgentStatus, string> = {
  offline: "bg-slate-700",
  waiting: "bg-amber-400",
  active: "animate-pulse bg-cyan-300",
  completed: "bg-emerald-400",
  skipped: "bg-slate-500",
  blocked: "bg-orange-400",
  paused: "bg-violet-400",
  error: "bg-rose-400",
};

export type AgentProfile = {
  id: string;
  name: string;
  title: string;
  description: string;
  parent_id: string | null;
  division: string;
  color: string;
  preferred_model: string;
  memory_namespace: string;
  tools: string[];
  capabilities: string[];
  delegates_to: string[];
  legacy_ids: string[];
  specialist?: boolean;
  status: AgentStatus;
};
