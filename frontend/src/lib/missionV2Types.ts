export type MissionStatus =
  | "draft"
  | "planning"
  | "ready"
  | "running"
  | "waiting_approval"
  | "blocked"
  | "validating"
  | "completed"
  | "failed"
  | "cancelled";

export type WorkItemStatus =
  | "queued"
  | "ready"
  | "active"
  | "review"
  | "retrying"
  | "completed"
  | "skipped"
  | "blocked";

export type GateStatus = "pending" | "running" | "passed" | "failed" | "skipped";
export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired" | "executed";
export type RiskLevel = 0 | 1 | 2 | 3;

export interface MissionV2 {
  id: string;
  goal: string;
  title?: string | null;
  project_id?: string | null;
  project_name?: string | null;
  status: MissionStatus;
  risk_level: RiskLevel;
  success_criteria?: string[];
  deadline?: string | null;
  budget_cents?: number;
  spent_cents?: number;
  costs?: { spent_cents?: number; reserved_cents?: number } | number;
  progress?: number;
  created_at: string;
  updated_at?: string;
  completed_at?: string | null;
  work_items?: WorkItemV2[];
  assignments?: AgentAssignmentV2[];
  quality_gates?: QualityGateV2[];
  artifacts?: MissionArtifactV2[];
}

export interface WorkItemV2 {
  id: string;
  key?: string;
  mission_id: string;
  title: string;
  description?: string;
  assigned_agent: string;
  agent_id?: string;
  status: WorkItemStatus;
  dependencies: string[];
  acceptance_criteria?: string[];
  expected_artifacts?: string[];
  progress?: number;
  skip_reason?: string | null;
  blocker?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface AgentAssignmentV2 {
  id: string;
  mission_id: string;
  work_item_id: string;
  agent_id: string;
  agent_name?: string;
  status: WorkItemStatus;
  progress?: number;
  current_action?: string | null;
  tool_calls?: number;
  estimated_seconds_remaining?: number | null;
  started_at?: string | null;
}

export interface QualityGateV2 {
  id: string;
  mission_id: string;
  work_item_id?: string | null;
  name: string;
  category?: string;
  status: GateStatus;
  required: boolean;
  summary?: string | null;
}

export interface ApprovalV2 {
  id: string;
  mission_id: string;
  title: string;
  description?: string;
  action_type: string;
  risk_level: RiskLevel;
  status: ApprovalStatus;
  target?: string | null;
  amount_cents?: number | null;
  preview?: Record<string, unknown> | null;
  summary?: string | null;
  payload_preview?: Record<string, unknown> | null;
  created_at: string;
  expires_at?: string | null;
}

export interface MissionArtifactV2 {
  id: string;
  mission_id: string;
  name: string;
  artifact_type: string;
  preview_url?: string | null;
  external_url?: string | null;
  created_at: string;
}

export interface BudgetV2 {
  month: string;
  limit_cents: number;
  monthly_limit_cents?: number;
  spent_cents: number;
  reserved_cents?: number;
  local_model_calls?: number;
  external_model_calls?: number;
  estimated_cents?: number;
  actual_cents?: number;
  remaining_cents?: number;
}

export interface CreateMissionV2 {
  goal: string;
  project_id?: string | null;
  deadline?: string | null;
  budget_cents: number;
  autonomy_level: RiskLevel;
  success_criteria?: string[];
}

export interface MissionCollection<T> {
  items: T[];
  total?: number;
}

export function collectionItems<T>(value: T[] | MissionCollection<T> | null | undefined): T[] {
  if (Array.isArray(value)) return value;
  return value?.items ?? [];
}

export function boundedProgress(value: number | undefined): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value ?? 0)));
}

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord {
  return value && typeof value === "object" ? value as UnknownRecord : {};
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function numberValue(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function normalizeWorkItem(value: unknown, missionId = ""): WorkItemV2 {
  const raw = record(value);
  return {
    id: text(raw.id),
    key: text(raw.key, text(raw.id)),
    mission_id: text(raw.mission_id, missionId),
    title: text(raw.title, text(raw.description, "Arbeitspaket")),
    description: text(raw.description),
    assigned_agent: text(raw.assigned_agent, text(raw.agent_id, "BOSS")),
    agent_id: text(raw.agent_id, text(raw.assigned_agent)),
    status: text(raw.status, "queued") as WorkItemStatus,
    dependencies: stringList(raw.dependencies),
    acceptance_criteria: stringList(raw.acceptance_criteria),
    expected_artifacts: stringList(raw.expected_artifacts),
    progress: numberValue(raw.progress),
    skip_reason: text(raw.skip_reason) || null,
    blocker: text(raw.blocker) || null,
    started_at: text(raw.started_at) || null,
    completed_at: text(raw.completed_at) || null,
  };
}

export function normalizeMission(value: unknown): MissionV2 {
  const raw = record(value);
  const id = text(raw.id);
  const workItems = Array.isArray(raw.work_items) ? raw.work_items.map((item) => normalizeWorkItem(item, id)) : [];
  return {
    ...raw,
    id,
    goal: text(raw.goal, text(raw.title, "Mission")),
    title: text(raw.title) || null,
    status: text(raw.status, "draft") as MissionStatus,
    risk_level: numberValue(raw.risk_level) as RiskLevel,
    progress: typeof raw.progress === "object" ? numberValue(record(raw.progress).percent) : numberValue(raw.progress),
    budget_cents: numberValue(raw.budget_cents),
    spent_cents: numberValue(raw.spent_cents),
    created_at: text(raw.created_at, new Date().toISOString()),
    deadline: text(raw.deadline) || null,
    success_criteria: stringList(raw.success_criteria),
    work_items: workItems,
    assignments: Array.isArray(raw.assignments) ? raw.assignments as unknown as AgentAssignmentV2[] : [],
    quality_gates: Array.isArray(raw.quality_gates) ? raw.quality_gates as unknown as QualityGateV2[] : [],
    artifacts: Array.isArray(raw.artifacts) ? raw.artifacts as unknown as MissionArtifactV2[] : [],
  } as MissionV2;
}

export function normalizeApproval(value: unknown): ApprovalV2 {
  const raw = record(value);
  return {
    id: text(raw.id),
    mission_id: text(raw.mission_id),
    title: text(raw.title, text(raw.summary, "Externe Aktion freigeben")),
    description: text(raw.description, text(raw.summary)),
    action_type: text(raw.action_type, "external_action"),
    risk_level: numberValue(raw.risk_level, 2) as RiskLevel,
    status: text(raw.status, "pending") as ApprovalStatus,
    target: text(raw.target) || null,
    amount_cents: typeof raw.amount_cents === "number" ? raw.amount_cents : null,
    preview: record(raw.preview ?? raw.payload_preview),
    summary: text(raw.summary) || null,
    payload_preview: record(raw.payload_preview),
    created_at: text(raw.created_at, new Date().toISOString()),
  };
}

export function normalizeBudget(value: unknown): BudgetV2 {
  const raw = record(value);
  const limit = numberValue(raw.limit_cents, numberValue(raw.monthly_limit_cents, 2000));
  return {
    month: text(raw.month, new Date().toISOString().slice(0, 7)),
    limit_cents: limit,
    monthly_limit_cents: limit,
    spent_cents: numberValue(raw.spent_cents, numberValue(raw.actual_cents)),
    reserved_cents: numberValue(raw.reserved_cents),
    estimated_cents: numberValue(raw.estimated_cents),
    actual_cents: numberValue(raw.actual_cents, numberValue(raw.spent_cents)),
    remaining_cents: numberValue(raw.remaining_cents, Math.max(0, limit - numberValue(raw.actual_cents, numberValue(raw.spent_cents)))),
    local_model_calls: numberValue(raw.local_model_calls),
    external_model_calls: numberValue(raw.external_model_calls),
  };
}
