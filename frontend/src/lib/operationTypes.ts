import type { AgentRun } from "./runStore";

export type OperationQuestion = {
  field: string;
  question: string;
  placeholder?: string;
};

export type OperationRoute = {
  kind: "coding" | "business";
  workflow: "run_engine" | "website_sales" | "mission_router";
  confidence: number;
  signals: string[];
};

export type OperationIntakeResponse = {
  status: "needs_input" | "run_created" | "project_created";
  route: OperationRoute;
  message?: string;
  questions?: OperationQuestion[];
  run?: AgentRun;
  project_id?: string;
  mission_plan_id?: string;
  task_count?: number;
  required_integrations?: Array<{ id: string; ready: boolean }>;
};
