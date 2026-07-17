export type ProjectStatus = "idea" | "planning" | "active" | "paused" | "completed" | "archived";
export type ProjectTaskStatus = "backlog" | "planned" | "queued" | "in_progress" | "blocked" | "review" | "completed" | "cancelled";
export type ProjectTaskType = "general" | "coding" | "research" | "design" | "automation" | "business" | "data" | "security" | "devops";

export type ProjectTask = {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: ProjectTaskStatus;
  priority: number;
  task_type: ProjectTaskType;
  assigned_agent: string | null;
  run_id: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
  executable: boolean;
  result: Record<string, unknown> | null;
  dependencies: string[];
};

export type ProjectArtifact = {
  id: string;
  project_id: string;
  task_id: string;
  run_id: string;
  name: string;
  artifact_type: string;
  media_type: string;
  size_bytes: number;
  sync_status: "local" | "pending" | "synced" | "failed";
  external_url: string | null;
  preview_available: boolean;
  preview_kind: "website" | "document";
  created_at: string;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  goal: string;
  category: string;
  status: ProjectStatus;
  workspace: string;
  owner_agent: string | null;
  deadline: string | null;
  budget_cents: number;
  revenue_target_cents: number;
  autopilot_enabled: boolean;
  delivery_status: "pending" | "syncing" | "synced" | "failed" | "local";
  delivery_error: string;
  delivery_progress: number;
  delivery_synced: number;
  delivery_total: number;
  delivery_synced_at: string | null;
  drive_url: string | null;
  progress: number;
  task_counts: Partial<Record<ProjectTaskStatus, number>>;
  active_agents: string[];
  tasks: ProjectTask[];
  artifacts: ProjectArtifact[];
  created_at: string;
  updated_at: string;
};
