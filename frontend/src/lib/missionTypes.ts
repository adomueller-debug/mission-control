import type { ProjectTaskType } from "./projectTypes";

export type SecretStatus = {
  names: string[];
  configured: boolean;
  configured_name: string | null;
};

export type Integration = {
  id: string;
  name: string;
  category: string;
  description: string;
  owner_agent: string;
  account_required: boolean;
  cost: string;
  setup_steps: string[];
  configurable_keys: string[];
  status: "ready" | "missing";
  ready: boolean;
  detected: boolean;
  secrets: SecretStatus[];
};

export type IntegrationRequirement = {
  id: string;
  project_id: string;
  integration_id: string;
  purpose: string;
  required: boolean;
  status: "ready" | "missing";
  ready: boolean;
  integration: Integration;
  created_at: string;
};

export type MissionPlanTask = {
  id: string;
  sequence: number;
  title: string;
  description: string;
  agent_id: string;
  task_type: ProjectTaskType;
  priority: number;
  dependencies: number[];
  integration_ids: string[];
  acceptance_criteria: string;
  delegation_path: string[];
};

export type MissionPlan = {
  id: string;
  project_id: string;
  goal: string;
  summary: string;
  strategy: string;
  assumptions: string[];
  risks: string[];
  success_metrics: string[];
  status: "draft" | "approved" | "rejected";
  planner_mode: "ollama" | "fallback";
  tasks: MissionPlanTask[];
  created_at: string;
  updated_at: string;
};
