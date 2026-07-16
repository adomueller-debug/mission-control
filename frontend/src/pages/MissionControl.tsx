import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  Ban,
  Bot,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  Clock3,
  Code2,
  Download,
  FolderCode,
  FolderKanban,
  GitBranch,
  GitPullRequest,
  Network,
  LayoutDashboard,
  Play,
  PlugZap,
  RefreshCw,
  Settings2,
  Sparkles,
  TerminalSquare,
  Wifi,
  WifiOff,
  Wrench,
  XCircle,
} from "lucide-react";

import { AgentGlyph } from "../components/agents/AgentGlyph";
import { AgentTeamView } from "../components/agents/AgentTeamView";
import { ProjectPortfolioView } from "../components/projects/ProjectPortfolioView";
import { IntegrationCenter } from "../components/integrations/IntegrationCenter";
import { InternalWorkView } from "../components/internal/InternalWorkView";
import { CommandCenterView } from "../components/overview/CommandCenterView";
import { MissionControlV2 } from "../components/v2/MissionControlV2";
import { useMissionControlSocket } from "../hooks/useMissionControlSocket";
import {
  AGENT_STATUS_DOTS,
  AGENT_STATUS_LABELS,
  type AgentProfile,
} from "../lib/agentTypes";
import { api } from "../lib/api";
import type { OperationIntakeResponse, OperationQuestion } from "../lib/operationTypes";
import {
  reportUrl,
  type AgentRun,
  type RunEvent,
  type RunStatus,
  useRunStore,
} from "../lib/runStore";

type Health = {
  version: string;
  status: string;
  services: Record<string, { ok: boolean; version?: string; models?: number }>;
};

type RuntimeConfig = {
  default_workspace: string;
  model: string;
  defaults: {
    timeout_seconds: number;
    max_tool_calls: number;
    max_repair_attempts: number;
  };
};

type Plan = {
  summary?: string;
  steps?: Array<{ id: number; title: string; description: string; agent: string; status: string }>;
};

type DiffPreview = {
  run_id: string;
  source_workspace: string;
  files: string[];
  diff: string;
  untracked_files: string[];
  can_apply: boolean;
};

const terminal = new Set<RunStatus>(["completed", "failed", "cancelled"]);
const statusLabel: Record<RunStatus, string> = {
  queued: "Wartet",
  planning: "Plant",
  executing: "Implementiert",
  validating: "Prüft",
  publishing: "Veröffentlicht",
  completed: "Erfolgreich",
  failed: "Fehlgeschlagen",
  cancelled: "Abgebrochen",
};

function toneForStatus(status: RunStatus) {
  if (status === "completed") return "emerald";
  if (status === "failed" || status === "cancelled") return "rose";
  if (status === "queued") return "slate";
  return "cyan";
}

const dotTone = {
  emerald: "bg-emerald-400",
  rose: "bg-rose-400",
  cyan: "bg-cyan-400",
  slate: "bg-slate-400",
};

const badgeTone = {
  emerald: "bg-emerald-400/10 text-emerald-300",
  rose: "bg-rose-400/10 text-rose-300",
  cyan: "bg-cyan-400/10 text-cyan-300",
  slate: "bg-slate-400/10 text-slate-300",
};

export default function MissionControl() {
  const {
    runs,
    activeRun,
    events,
    error,
    loadRuns,
    selectRun,
    cancelRun,
    resumeRun,
    addEvent,
    updateActive,
  } = useRunStore();
  const [task, setTask] = useState("");
  const [publish, setPublish] = useState(false);
  const [workspace, setWorkspace] = useState(".");
  const [timeoutSeconds, setTimeoutSeconds] = useState(1200);
  const [maxToolCalls, setMaxToolCalls] = useState(50);
  const [maxRepairAttempts, setMaxRepairAttempts] = useState(5);
  const [model, setModel] = useState("qwen2.5:7b");
  const [health, setHealth] = useState<Health | null>(null);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [runAgents, setRunAgents] = useState<AgentProfile[]>([]);
  const [operationBusy, setOperationBusy] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [operationQuestions, setOperationQuestions] = useState<OperationQuestion[]>([]);
  const [operationAnswers, setOperationAnswers] = useState<Record<string, string>>({});
  const [businessResult, setBusinessResult] = useState<OperationIntakeResponse | null>(null);
  const [projectToOpen, setProjectToOpen] = useState<string | null>(null);
  const [projectCreateRequest, setProjectCreateRequest] = useState(0);
  const [view, setView] = useState<"overview" | "missions" | "operations" | "internal" | "projects" | "integrations" | "team">("overview");
  const [runFilter, setRunFilter] = useState<"attention" | "active" | "history">("attention");
  const [pendingRunIds, setPendingRunIds] = useState<Set<string>>(new Set());
  const [dismissedRunIds, setDismissedRunIds] = useState<Set<string>>(() => {
    try {
      return new Set<string>(JSON.parse(window.localStorage.getItem("mission-control-dismissed-runs") ?? "[]"));
    } catch {
      return new Set<string>();
    }
  });

  const onEvent = useCallback((event: RunEvent) => addEvent(event), [addEvent]);
  const onSnapshot = useCallback((run: AgentRun) => updateActive(run), [updateActive]);
  const socketConnected = useMissionControlSocket(activeRun?.id ?? null, onEvent, onSnapshot);
  const backendConnected = ["ok", "healthy", "degraded"].includes(health?.status ?? "");

  useEffect(() => {
    void loadRuns();
    void api<Health>("/api/v1/health").then(setHealth).catch(() => setHealth(null));
    const loadAgents = () => void api<AgentProfile[]>("/api/v1/agents").then(setAgents).catch(() => setAgents([]));
    loadAgents();
    const agentTimer = window.setInterval(loadAgents, 3000);
    void api<RuntimeConfig>("/api/v1/config")
      .then((config) => {
        setWorkspace(config.default_workspace);
        setModel(config.model);
        setTimeoutSeconds(config.defaults.timeout_seconds);
        setMaxToolCalls(config.defaults.max_tool_calls);
        setMaxRepairAttempts(config.defaults.max_repair_attempts);
      })
      .catch(() => undefined);
    return () => window.clearInterval(agentTimer);
  }, [loadRuns]);

  useEffect(() => {
    if (!activeRun) return;
    void api<AgentProfile[]>(`/api/v1/runs/${activeRun.id}/agents`)
      .then(setRunAgents)
      .catch(() => undefined);
    if (terminal.has(activeRun.status)) return;
    const timer = window.setInterval(() => void selectRun(activeRun.id), 3000);
    return () => window.clearInterval(timer);
  }, [activeRun, selectRun]);

  useEffect(() => {
    let cancelled = false;
    const completed = runs.filter((run) => run.status === "completed").slice(0, 20);
    void Promise.all(completed.map(async (run) => {
      try {
        const [preview, runEvents] = await Promise.all([
          api<DiffPreview>(`/api/v1/runs/${run.id}/diff`),
          api<RunEvent[]>(`/api/v1/runs/${run.id}/events`),
        ]);
        return preview.can_apply && !runEvents.some((event) => event.type === "changes.applied") ? run.id : null;
      } catch {
        return null;
      }
    })).then((ids) => {
      if (!cancelled) setPendingRunIds(new Set(ids.filter((id): id is string => Boolean(id))));
    });
    return () => { cancelled = true; };
  }, [runs]);

  const eventList = useMemo(() => events.slice().reverse(), [events]);
  const activeRuns = runs.filter((run) => !terminal.has(run.status));
  const activeCount = activeRuns.length;
  const successfulCount = runs.filter((run) => run.status === "completed").length;
  const successRate = runs.length ? Math.round((successfulCount / runs.length) * 100) : 0;
  const attentionRuns = runs.filter((run) => !dismissedRunIds.has(run.id) && (pendingRunIds.has(run.id) || run.status === "failed"));
  const pendingDecisionCount = attentionRuns.filter((run) => pendingRunIds.has(run.id)).length;
  const filteredRuns = (runFilter === "attention" ? attentionRuns : runFilter === "active" ? runs.filter((run) => !terminal.has(run.status)) : runs.filter((run) => terminal.has(run.status))).slice(0, 12);

  function dismissRun(runId: string) {
    dismissRuns([runId]);
  }

  function dismissRuns(runIds: string[]) {
    setDismissedRunIds((current) => {
      const next = new Set(current);
      runIds.forEach((runId) => next.add(runId));
      window.localStorage.setItem("mission-control-dismissed-runs", JSON.stringify([...next]));
      return next;
    });
  }

  async function submit() {
    if (!task.trim()) return;
    setOperationBusy(true);
    setOperationError(null);
    setBusinessResult(null);
    try {
      const result = await api<OperationIntakeResponse>("/api/v1/operations/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: task.trim(),
          workspace,
          answers: operationAnswers,
          options: {
            publish,
            timeout_seconds: timeoutSeconds,
            max_tool_calls: maxToolCalls,
            max_repair_attempts: maxRepairAttempts,
          },
        }),
      });
      if (result.status === "needs_input") {
        setOperationQuestions(result.questions ?? []);
        return;
      }
      setOperationQuestions([]);
      setOperationAnswers({});
      if (result.status === "run_created" && result.run) {
        await loadRuns();
        await selectRun(result.run.id);
        setTask("");
        return;
      }
      if (result.status === "project_created") {
        setBusinessResult(result);
        setProjectToOpen(result.project_id ?? null);
        setTask("");
      }
    } catch (reason) {
      setOperationError(reason instanceof Error ? reason.message : "Mission konnte nicht geroutet werden");
    } finally {
      setOperationBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#080b10] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_52%_-12%,rgba(34,211,238,0.09),transparent_34%)]" />
      <div className="relative mx-auto flex min-h-screen max-w-[1720px]">
        <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-white/[0.07] bg-[#080b10]/72 px-5 py-6 backdrop-blur-2xl lg:flex lg:flex-col">
          <Brand version={health?.version} />

          <nav className="mt-10 space-y-1">
            <NavItem active={view === "overview"} onClick={() => setView("overview")} icon={<LayoutDashboard size={17} />} label="Übersicht" />
            <NavItem active={view === "missions"} onClick={() => setView("missions")} icon={<Network size={17} />} label="Missionen 2.0" />
            <NavItem active={view === "operations"} onClick={() => setView("operations")} icon={<Activity size={17} />} label="Operations" />
            <NavItem active={view === "internal"} onClick={() => setView("internal")} icon={<Wrench size={17} />} label="Intern" badge={runs.filter((run) => run.workstream === "internal" && !terminal.has(run.status)).length || undefined} />
            <NavItem active={view === "projects"} onClick={() => setView("projects")} icon={<FolderKanban size={17} />} label="Projekte" />
            <NavItem active={view === "integrations"} onClick={() => setView("integrations")} icon={<PlugZap size={17} />} label="Integrationen" />
            <NavItem active={view === "team"} onClick={() => setView("team")} icon={<Bot size={17} />} label="Agenten" badge={agents.length} />
          </nav>

          <div className="mt-9">
            <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-600">
              Agent Team
            </p>
            <div className="mt-3 max-h-[460px] space-y-1 overflow-auto">
              {agents.filter((agent) => !agent.specialist).map((agent) => <AgentRow key={agent.id} agent={agent} />)}
            </div>
          </div>

          <div className="mc-glass mt-auto rounded-2xl p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              {backendConnected ? <Wifi size={15} className="text-emerald-400" /> : <WifiOff size={15} className="text-rose-400" />}
              Lokale Runtime
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Ollama, Git und Datenbank werden lokal orchestriert.
            </p>
          </div>
        </aside>

        <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div className="lg:hidden"><Brand version={health?.version} /></div>
            <div className="hidden lg:block">
              <p className="text-sm text-slate-500">Autonomous agent organization</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">{view === "overview" ? "Command Center" : view === "missions" ? "Mission Engine" : view === "operations" ? "Operations" : view === "internal" ? "Internal Operations" : view === "projects" ? "Project Portfolio" : view === "integrations" ? "Integration Center" : "Agent Network"}</h1>
            </div>
            <div className="mc-glass flex items-center gap-2 rounded-full px-3 py-2 text-xs text-slate-400">
              <span className={`h-1.5 w-1.5 rounded-full ${backendConnected ? "bg-emerald-400" : "bg-rose-400"}`} />
              Backend
              <span className="mx-1 h-3 w-px bg-white/10" />
              <span className={`h-1.5 w-1.5 rounded-full ${socketConnected ? "bg-cyan-400" : "bg-slate-600"}`} />
              {socketConnected ? "Live" : "Standby"}
            </div>
          </header>

          <div className="mt-5 grid grid-cols-3 gap-2 lg:hidden">
            <NavItem active={view === "overview"} onClick={() => setView("overview")} icon={<LayoutDashboard size={16} />} label="Übersicht" />
            <NavItem active={view === "missions"} onClick={() => setView("missions")} icon={<Network size={16} />} label="Missionen" />
            <NavItem active={view === "operations"} onClick={() => setView("operations")} icon={<Activity size={16} />} label="Operations" />
            <NavItem active={view === "internal"} onClick={() => setView("internal")} icon={<Wrench size={16} />} label="Intern" />
            <NavItem active={view === "projects"} onClick={() => setView("projects")} icon={<FolderKanban size={16} />} label="Projekte" />
            <NavItem active={view === "integrations"} onClick={() => setView("integrations")} icon={<PlugZap size={16} />} label="Integrationen" />
            <NavItem active={view === "team"} onClick={() => setView("team")} icon={<Bot size={16} />} label="Agenten" badge={agents.length} />
          </div>

          {view === "overview" ? (
            <CommandCenterView
              agents={agents}
              runs={runs}
              backendConnected={backendConnected}
              healthyServices={Object.values(health?.services ?? {}).filter((service) => service.ok).length}
              totalServices={Object.keys(health?.services ?? {}).length}
              decisionCount={attentionRuns.length}
              onNewMission={() => setView("operations")}
              onProjects={() => setView("projects")}
              onCreateProject={() => {
                setView("projects");
                setProjectCreateRequest((value) => value + 1);
              }}
              onIntegrations={() => setView("integrations")}
            />
          ) : view === "missions" ? (
            <MissionControlV2 />
          ) : view === "team" ? (
            <AgentTeamView agents={agents} />
          ) : view === "internal" ? (
            <InternalWorkView
              runs={runs}
              agents={agents}
              onOpenRun={(runId) => {
                void selectRun(runId);
                setView("operations");
              }}
              onNewInternal={() => {
                setTask("Verbessere Mission Control intern: ");
                setView("operations");
              }}
            />
          ) : view === "projects" ? (
            <ProjectPortfolioView
              agents={agents}
              defaultWorkspace={workspace}
              initialProjectId={projectToOpen}
              createRequest={projectCreateRequest}
              onOpenRun={(runId) => {
                void selectRun(runId);
                setView("operations");
              }}
            />
          ) : view === "integrations" ? (
            <IntegrationCenter agents={agents} />
          ) : (
            <>
          <OperationsLiveStrip runs={activeRuns} agents={agents} onOpen={(runId) => void selectRun(runId)} />
          {(error || operationError) && (
            <div className="mt-6 flex items-center gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              <XCircle size={17} /> {operationError ?? error}
            </div>
          )}

          <section className="mc-enter mc-shimmer mc-glass relative mt-4 overflow-hidden rounded-[24px] p-1">
            <div className="rounded-[18px] bg-[#0c1016] p-4 sm:p-5">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-sm font-medium text-cyan-300"><Sparkles size={16} /> Neue Mission</div>
                <div className="flex flex-wrap gap-2 sm:ml-auto">
                <PromptChip label="Mission Control verbessern" onClick={() => setTask("Verbessere Mission Control wie folgt: ")} />
                <PromptChip label="Website-Vertrieb starten" onClick={() => setTask("Finde und qualifiziere lokale Unternehmen in Heidelberg mit fehlender oder schwacher Website und bereite passende Website-Angebote vor.")} />
                <PromptChip label="Fehler beheben" onClick={() => setTask("Analysiere und behebe folgenden Fehler inklusive Regressionstest: ")} />
                <PromptChip label="Tests ergänzen" onClick={() => setTask("Ergänze fehlende automatisierte Tests für: ")} />
                </div>
              </div>
              <textarea
                value={task}
                onChange={(event) => setTask(event.target.value)}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void submit();
                }}
                placeholder="Was soll dein Agententeam analysieren, bauen und validieren?"
                className="mt-3 min-h-16 w-full resize-y bg-transparent text-base leading-6 text-slate-100 outline-none placeholder:text-slate-600"
              />
              {operationQuestions.length > 0 && (
                <div className="mb-4 rounded-2xl border border-amber-300/15 bg-amber-300/[0.035] p-4">
                  <div className="flex items-center gap-2 text-xs font-medium text-amber-200">
                    <Bot size={14} /> BOSS benötigt noch Kontext
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {operationQuestions.map((question) => (
                      <label key={question.field} className="text-[11px] leading-5 text-slate-400">
                        {question.question}
                        <input
                          value={operationAnswers[question.field] ?? ""}
                          onChange={(event) => setOperationAnswers((current) => ({ ...current, [question.field]: event.target.value }))}
                          placeholder={question.placeholder}
                          className="mt-1.5 w-full rounded-lg border border-white/[0.08] bg-[#080b10] px-3 py-2 text-xs text-slate-200 outline-none focus:border-amber-300/30"
                        />
                      </label>
                    ))}
                  </div>
                </div>
              )}
              {businessResult?.status === "project_created" && (
                <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.035] p-4">
                  <div className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-300/10 text-emerald-300"><BriefcaseBusiness size={16} /></div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-emerald-100">Mission angenommen</p>
                    <p className="mt-1 text-[11px] text-slate-500">{businessResult.phase === "planning" ? "BOSS plant und delegiert jetzt automatisch im Hintergrund." : `BOSS hat ${businessResult.task_count ?? 0} Aufgaben delegiert.`} Externe E-Mails bleiben Entwürfe.</p>
                  </div>
                  <button type="button" onClick={() => setView("projects")} className="mc-button-primary mc-arrow-action flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold">
                    Projekt öffnen <ArrowRight size={13} />
                  </button>
                </div>
              )}
              <details className="mb-4 rounded-xl border border-white/[0.06] bg-black/10">
                <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-xs text-slate-500">
                  <Settings2 size={14} /> Run-Konfiguration
                  <span className="ml-auto text-[10px] text-slate-700">{model}</span>
                </summary>
                <div className="grid gap-3 border-t border-white/[0.06] p-3 sm:grid-cols-3">
                  <label className="sm:col-span-3">
                    <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-600"><FolderCode size={12} /> Workspace</span>
                    <input value={workspace} onChange={(event) => setWorkspace(event.target.value)} className="mt-1.5 w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-3 py-2 text-xs text-slate-300 outline-none focus:border-cyan-300/30" />
                  </label>
                  <NumberField label="Timeout (Sek.)" value={timeoutSeconds} min={30} max={7200} onChange={setTimeoutSeconds} />
                  <NumberField label="Tool-Aufrufe" value={maxToolCalls} min={1} max={500} onChange={setMaxToolCalls} />
                  <NumberField label="Reparaturen" value={maxRepairAttempts} min={0} max={10} onChange={setMaxRepairAttempts} />
                </div>
              </details>
              <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.07] pt-4">
                <label className="flex cursor-pointer items-center gap-3 text-sm text-slate-400">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={publish}
                    onClick={() => setPublish((value) => !value)}
                    className={`relative h-6 w-11 rounded-full border transition ${publish ? "border-cyan-200/60 bg-cyan-400 shadow-[0_0_18px_rgba(34,211,238,0.25)]" : "border-white/[0.07] bg-slate-800 shadow-inner"}`}
                  >
                    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-md transition-all duration-300 ${publish ? "left-[21px]" : "left-0.5"}`} />
                  </button>
                  PR nach grünen Checks veröffentlichen
                </label>
                <button
                  onClick={() => void submit()}
                  disabled={operationBusy || !task.trim() || operationQuestions.some((question) => !(operationAnswers[question.field] ?? "").trim())}
                  className="mc-button-primary group flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-30"
                >
                  {operationBusy ? <RefreshCw className="animate-spin" size={16} /> : <Play size={15} fill="currentColor" />}
                  Mission starten
                  <span className="text-xs text-slate-500 group-hover:text-cyan-900">⌘↵</span>
                </button>
              </div>
            </div>
          </section>

          <section className="mc-enter mc-panel mt-5 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-4">
              <div className={`grid h-10 w-10 place-items-center rounded-xl ${attentionRuns.length ? "bg-amber-300/10 text-amber-300" : "bg-emerald-400/10 text-emerald-300"}`}>
                {attentionRuns.length ? <Clock3 size={18} /> : <CheckCircle2 size={18} />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">Deine Aktion erforderlich</p>
                <p className="mt-1 text-sm font-medium text-slate-200">{attentionRuns.length ? `${attentionRuns.length} Run${attentionRuns.length === 1 ? "" : "s"} benötigen eine Entscheidung` : "Keine offene Freigabe"}</p>
                <p className="mt-1 text-[11px] leading-5 text-slate-600">{pendingDecisionCount ? `${pendingDecisionCount} validierte Änderung${pendingDecisionCount === 1 ? " liegt" : "en liegen"} noch isoliert und wurde noch nicht ins Hauptprojekt übernommen.` : attentionRuns.some((run) => run.status === "failed") ? "Mindestens eine fehlgeschlagene Mission sollte geprüft oder neu gestartet werden." : activeCount ? "Die Agenten arbeiten selbstständig. Du musst momentan nichts tun." : "BOSS und das Agententeam sind bereit für eine neue Mission."}</p>
              </div>
              {attentionRuns[0] && <div className="flex flex-wrap items-center gap-2">{pendingDecisionCount > 1 && <button onClick={() => dismissRuns(attentionRuns.filter((run) => pendingRunIds.has(run.id)).map((run) => run.id))} className="mc-button rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-400 hover:text-slate-200" title="Entfernt nur die Freigaben aus dieser Ansicht; Runs bleiben im Verlauf">Alle im Verlauf behalten</button>}<button onClick={() => { void selectRun(attentionRuns[0].id); setRunFilter("attention"); }} className="mc-button-primary mc-arrow-action flex items-center gap-2 rounded-xl px-3.5 py-2.5 text-xs font-semibold">Entscheidung öffnen <ArrowRight size={13} /></button></div>}
            </div>
          </section>

          <section className="mt-4 grid grid-cols-3 gap-3">
            <Metric label="Aktive Missionen" value={activeCount} detail={activeCount ? "Agenten arbeiten" : "System bereit"} icon={<Clock3 size={17} />} />
            <Metric label="Aktion nötig" value={attentionRuns.length} detail={attentionRuns.length ? "Prüfen oder fortsetzen" : "Nichts offen"} icon={<Activity size={17} />} />
            <Metric label="Erfolgsquote" value={`${successRate}%`} detail={`${successfulCount} abgeschlossen`} icon={<CheckCircle2 size={17} />} />
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
            <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3">
              <div className="px-2 py-2">
                <div className="flex items-center justify-between"><h2 className="text-sm font-semibold">Missionen</h2><span className="text-xs text-slate-600">{runs.length}</span></div>
                <div className="mc-segment mt-3 grid grid-cols-3 rounded-xl p-1 text-[10px]">
                  <RunFilterButton label="Aktion" count={attentionRuns.length} active={runFilter === "attention"} onClick={() => setRunFilter("attention")} />
                  <RunFilterButton label="Aktiv" count={activeCount} active={runFilter === "active"} onClick={() => setRunFilter("active")} />
                  <RunFilterButton label="Verlauf" count={runs.filter((run) => terminal.has(run.status)).length} active={runFilter === "history"} onClick={() => setRunFilter("history")} />
                </div>
              </div>
              <div className="mt-2 max-h-[720px] space-y-1 overflow-auto">
                {filteredRuns.map((run) => (
                  <RunRow
                    key={run.id}
                    run={run}
                    selected={activeRun?.id === run.id}
                    onClick={() => void selectRun(run.id)}
                  />
                ))}
                {filteredRuns.length === 0 && <EmptyState text={runFilter === "attention" ? "Keine Entscheidung offen." : runFilter === "active" ? "Keine aktive Mission." : "Noch kein Verlauf."} />}
              </div>
            </div>

            <div className="mc-panel min-w-0 rounded-2xl border border-white/[0.07] bg-white/[0.025]">
              {activeRun ? (
                <RunWorkspace
                  key={activeRun.id}
                  run={activeRun}
                  agents={runAgents.length ? runAgents : agents}
                  events={eventList}
                  onCancel={() => void cancelRun()}
                  onResume={() => void resumeRun()}
                  onDismiss={() => dismissRun(activeRun.id)}
                />
              ) : (
                <div className="flex min-h-[520px] items-center justify-center"><EmptyState text="Wähle nur dann eine Mission, wenn du Details oder eine Entscheidung prüfen möchtest." /></div>
              )}
            </div>
          </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function Brand({ version }: { version?: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-300">
        <Bot size={21} />
      </div>
      <div>
        <p className="font-semibold tracking-tight">Mission Control</p>
        <p className="text-[11px] text-slate-600">Local AI Platform {version ? `· v${version}` : ""}</p>
      </div>
    </div>
  );
}

function NavItem({ icon, label, active = false, badge, onClick }: { icon: React.ReactNode; label: string; active?: boolean; badge?: number; onClick?: () => void }) {
  return (
    <button type="button" onClick={onClick} className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${active ? "mc-nav-active text-slate-100" : "text-slate-500 hover:bg-white/[0.035] hover:text-slate-300"}`}>
      <span className={`transition-transform duration-300 ${active ? "text-cyan-300" : "group-hover:scale-110"}`}>{icon}</span><span>{label}</span>{badge !== undefined && <span className="ml-auto rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[10px]">{badge}</span>}
    </button>
  );
}

function AgentRow({ agent }: { agent: AgentProfile }) {
  return (
    <div className="group flex items-center gap-3 rounded-xl px-3 py-2.5">
      <AgentGlyph id={agent.id} color={agent.color} size="sm" active={agent.status === "active"} />
      <div className="min-w-0">
        <p className="text-sm text-slate-300">{agent.name}</p>
        <p className="truncate text-[11px] text-slate-600">{AGENT_STATUS_LABELS[agent.status]}</p>
      </div>
      <span className={`ml-auto h-1.5 w-1.5 rounded-full ${AGENT_STATUS_DOTS[agent.status]}`} />
    </div>
  );
}

function Metric({ label, value, detail, icon }: { label: string; value: string | number; detail: string; icon: React.ReactNode }) {
  return (
    <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
      <div className="flex items-center justify-between text-xs text-slate-500"><span>{label}</span>{icon}</div>
      <p className="mt-3 text-xl font-semibold tracking-tight capitalize text-slate-100">{value}</p>
      <p className="mt-1 text-[11px] text-slate-600">{detail}</p>
    </div>
  );
}

function missionTitle(task: string) {
  const assignment = task.match(/(?:^|\n)Aufgabe:\s*([^\n]+)/i)?.[1]?.trim();
  if (assignment) return assignment;
  const firstLine = task.split("\n").find((line) => line.trim())?.trim() ?? "Mission";
  return firstLine.length > 110 ? `${firstLine.slice(0, 107)}…` : firstLine;
}

function OperationsLiveStrip({ runs, agents, onOpen }: { runs: AgentRun[]; agents: AgentProfile[]; onOpen: (runId: string) => void }) {
  return (
    <section className="mc-enter mt-7 rounded-2xl border border-cyan-300/10 bg-cyan-300/[0.025] p-3.5">
      <div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${runs.length ? "animate-pulse bg-cyan-300" : "bg-emerald-400"}`} /><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Live Agent Operations</p><span className="ml-auto text-[10px] text-slate-600">{runs.length ? `${runs.length} aktiv` : "Bereit"}</span></div>
      {runs.length ? <div className="mt-3 grid gap-2 lg:grid-cols-2">{runs.slice(0, 4).map((run) => {
        const agent = agents.find((item) => item.id === run.current_step || item.legacy_ids.includes(run.current_step ?? ""));
        return <button key={run.id} onClick={() => onOpen(run.id)} className="mc-arrow-action flex min-w-0 items-center gap-3 rounded-xl border border-white/[0.06] bg-black/10 px-3 py-2.5 text-left hover:border-cyan-300/15"><AgentGlyph id={agent?.id ?? "boss"} color={agent?.color ?? "#67e8f9"} size="sm" active /><span className="min-w-0 flex-1"><span className="block text-[10px] font-semibold uppercase tracking-wider text-cyan-300/70">{agent?.name ?? "BOSS"} · {statusLabel[run.status]}</span><span className="mt-0.5 block truncate text-xs text-slate-300">{missionTitle(run.task)}</span></span><ChevronRight size={13} className="text-slate-600" /></button>;
      })}</div> : <p className="mt-2 text-xs text-slate-600">Kein Agent arbeitet gerade. Du kannst direkt eine neue Mission starten.</p>}
    </section>
  );
}

function RunRow({ run, selected, onClick }: { run: AgentRun; selected: boolean; onClick: () => void }) {
  const tone = toneForStatus(run.status);
  return (
    <button onClick={onClick} className={`mc-arrow-action group w-full rounded-xl border px-3 py-3 text-left ${selected ? "border-cyan-300/20 bg-cyan-300/[0.06] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]" : "border-transparent hover:bg-white/[0.035]"}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotTone[tone]} ${!terminal.has(run.status) && run.status !== "queued" ? "animate-pulse" : ""}`} />
        <span className="min-w-0 flex-1">
          <span className="block h-10 overflow-hidden text-sm leading-5 text-slate-300">{missionTitle(run.task)}</span>
          <span className="mt-2 flex items-center justify-between text-[11px] text-slate-600">
            <span>{statusLabel[run.status]}</span>
            <span>{new Date(run.created_at).toLocaleDateString("de-DE", { day: "2-digit", month: "short" })}</span>
          </span>
        </span>
        <ChevronRight size={14} className="mt-1 text-slate-700 group-hover:text-slate-500" />
      </div>
    </button>
  );
}

function RunFilterButton({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) {
  return <button onClick={onClick} className={`rounded-lg px-1.5 py-1.5 ${active ? "mc-segment-active text-slate-200" : "text-slate-600 hover:text-slate-400"}`}>{label}<span className="ml-1 text-slate-600">{count}</span></button>;
}

function RunWorkspace({ run, agents, events, onCancel, onResume, onDismiss }: { run: AgentRun; agents: AgentProfile[]; events: RunEvent[]; onCancel: () => void; onResume: () => void; onDismiss: () => void }) {
  const plan = run.plan as Plan | null;
  const files = run.result?.files ?? [];
  const artifacts = run.result?.artifacts ?? [];
  const findings = run.result?.findings ?? [];
  const nextActions = run.result?.next_actions ?? [];
  const [diff, setDiff] = useState<DiffPreview | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const alreadyApplied = applied || events.some((event) => event.type === "changes.applied");
  const codingRun = run.run_kind === "coding";
  const workflowAgents = codingRun
    ? (["boss", "forge_planner", "forge_builder", "forge_reviewer", "forge_publisher"]
        .map((id) => agents.find((agent) => agent.id === id))
        .filter(Boolean) as AgentProfile[])
    : agents.filter((agent) => agent.status !== "offline" && agent.status !== "skipped");

  useEffect(() => {
    if (run.status !== "completed") return;
    void api<DiffPreview>(`/api/v1/runs/${run.id}/diff`)
      .then(setDiff)
      .catch(() => setDiff(null));
  }, [run.id, run.status]);

  async function applyChanges() {
    if (!diff?.can_apply || alreadyApplied) return;
    const confirmed = window.confirm(
      `Die validierten Änderungen aus ${diff.files.length} Datei(en) nach ${diff.source_workspace} übernehmen und dort committen?`,
    );
    if (!confirmed) return;
    setApplying(true);
    setApplyError(null);
    try {
      await api(`/api/v1/runs/${run.id}/apply`, { method: "POST" });
      setApplied(true);
    } catch (error) {
      setApplyError(error instanceof Error ? error.message : "Änderungen konnten nicht übernommen werden.");
    } finally {
      setApplying(false);
    }
  }
  return (
    <div>
      <div className="border-b border-white/[0.07] p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <StatusBadge status={run.status} />
              <span>Run {run.id.slice(0, 8)}</span>
            </div>
            <h2 className="mt-3 text-lg font-semibold leading-7 text-slate-100">{missionTitle(run.task)}</h2>
            {missionTitle(run.task) !== run.task && <details className="mt-2 max-w-3xl rounded-lg border border-white/[0.05] bg-black/10"><summary className="cursor-pointer list-none px-3 py-2 text-[11px] text-slate-500">Vollständiges Missionsbriefing anzeigen</summary><p className="max-h-48 overflow-auto whitespace-pre-wrap border-t border-white/[0.05] px-3 py-3 text-[11px] leading-5 text-slate-500">{run.task}</p></details>}
          </div>
          <div className="flex items-center gap-2">
            {!terminal.has(run.status) && <ActionButton danger onClick={onCancel} icon={<Ban size={15} />} label="Stop" />}
            {(run.status === "failed" || run.status === "cancelled") && <ActionButton onClick={onResume} icon={<RefreshCw size={15} />} label="Fortsetzen" />}
            <a href={reportUrl(run.id)} className="mc-icon-button h-9 w-9 rounded-xl text-slate-400" title="Markdown-Report"><Download size={15} /></a>
            {run.pr_url && <a href={run.pr_url} target="_blank" rel="noreferrer" className="mc-icon-button h-9 w-9 rounded-xl text-slate-400" title="Pull Request"><GitPullRequest size={15} /></a>}
          </div>
        </div>

        <div className={`mt-6 grid gap-2 ${codingRun ? "grid-cols-2 sm:grid-cols-5" : "grid-cols-1 sm:max-w-sm"}`}>
          {workflowAgents.map((agent, index) => <AgentStage key={agent.id} agent={agent} last={index === workflowAgents.length - 1} />)}
        </div>

        {run.status === "completed" && diff?.can_apply && !alreadyApplied && (
          <div className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl border border-amber-300/20 bg-amber-300/[0.055] p-4">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-amber-300/10 text-amber-200"><GitBranch size={16} /></div>
            <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-amber-100">Deine Entscheidung: Änderungen übernehmen?</p><p className="mt-1 text-[11px] leading-5 text-slate-500">Der Agent hat validierte Änderungen in einem isolierten Workspace erstellt. Klicke nur dann auf „Änderungen übernehmen“, wenn dieses Ergebnis ins Hauptprojekt soll. Andernfalls ist keine Aktion nötig.</p></div>
            <button onClick={onDismiss} className="mc-button h-9 rounded-xl px-3 text-xs font-medium text-slate-400 hover:text-slate-200">Nur im Verlauf behalten</button>
            <button onClick={() => void applyChanges()} disabled={applying} className="mc-button-primary flex h-9 items-center gap-2 rounded-xl px-3 text-xs font-semibold disabled:opacity-50">{applying ? <RefreshCw size={14} className="animate-spin" /> : <Check size={14} />}Änderungen übernehmen</button>
          </div>
        )}
        {alreadyApplied && <div className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-400/15 bg-emerald-400/[0.045] px-4 py-3 text-xs text-emerald-300"><CheckCircle2 size={14} /> Änderungen wurden bereits ins Hauptprojekt übernommen und committed.</div>}
      </div>

      <div className="grid min-h-[500px] lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6 p-5 sm:p-6">
          <div className="grid grid-cols-3 gap-2">
            <CompactMetric label="Tool Calls" value={run.tool_calls} />
            <CompactMetric label="Reparaturen" value={run.repair_attempts} />
            <CompactMetric label="Publishing" value={run.publish ? "An" : "Aus"} />
          </div>

          {plan?.steps && (
            <section>
              <SectionTitle icon={<CircleDashed size={15} />} title="Execution Plan" />
              <div className="mt-3 space-y-2">
                {plan.steps.map((step) => (
                  <div key={step.id} className="flex gap-3 rounded-xl border border-white/[0.06] bg-black/10 p-3">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-white/[0.05] text-[11px] text-slate-500">{step.id}</span>
                    <div><p className="text-sm text-slate-300">{step.title}</p><p className="mt-0.5 text-xs text-slate-600">{step.description} · {step.agent}</p></div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {files.length > 0 && (
            <section>
              <SectionTitle icon={<Code2 size={15} />} title="Geänderte Dateien" />
              <div className="mt-3 overflow-hidden rounded-xl border border-white/[0.06]">
                {files.map((file) => <div key={file} className="flex items-center gap-3 border-b border-white/[0.05] px-3 py-2.5 text-xs text-slate-400 last:border-0"><Check size={13} className="text-emerald-400" />{file}</div>)}
              </div>
              {diff?.diff && (
                <details className="mt-2 rounded-xl border border-white/[0.06] bg-black/10">
                  <summary className="cursor-pointer list-none px-3 py-2.5 text-xs text-slate-500">Git-Diff anzeigen · {diff.files.length} Datei(en)</summary>
                  <pre className="max-h-96 overflow-auto border-t border-white/[0.06] p-4 text-[11px] leading-5 text-slate-400">{diff.diff}</pre>
                </details>
              )}
              {diff && !diff.can_apply && diff.untracked_files.length > 0 && (
                <p className="mt-2 rounded-lg bg-amber-400/[0.07] px-3 py-2 text-xs text-amber-200/70">Neue Dateien müssen derzeit über einen Pull Request übernommen werden: {diff.untracked_files.join(", ")}</p>
              )}
            </section>
          )}

          {(run.result?.summary || artifacts.length > 0 || findings.length > 0) && (
            <section>
              <SectionTitle icon={<Sparkles size={15} />} title="Arbeitsergebnis" />
              {run.result?.summary && <p className="mt-3 rounded-xl border border-white/[0.06] bg-black/10 p-4 text-sm leading-6 text-slate-300">{run.result.summary}</p>}
              {findings.length > 0 && (
                <div className="mt-3 space-y-2">
                  {findings.map((finding, index) => <div key={`${finding}-${index}`} className="flex gap-2.5 rounded-xl border border-white/[0.05] px-3 py-2.5 text-xs leading-5 text-slate-400"><CheckCircle2 size={13} className="mt-0.5 shrink-0 text-cyan-300" />{finding}</div>)}
                </div>
              )}
              {artifacts.map((artifact) => (
                <details key={artifact.title} className="mt-3 rounded-xl border border-white/[0.06] bg-black/10" open={artifacts.length === 1}>
                  <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-slate-300">{artifact.title}<span className="ml-2 text-[10px] uppercase tracking-wider text-slate-600">{artifact.artifact_type}</span></summary>
                  <div className="whitespace-pre-wrap border-t border-white/[0.06] p-4 text-xs leading-6 text-slate-400">{artifact.content}</div>
                </details>
              ))}
              {nextActions.length > 0 && <div className="mt-3 rounded-xl border border-cyan-300/10 bg-cyan-300/[0.025] p-4"><p className="text-[10px] uppercase tracking-wider text-cyan-300/60">Nächste Aktionen</p><ol className="mt-2 space-y-1.5 text-xs leading-5 text-slate-400">{nextActions.map((action, index) => <li key={`${action}-${index}`}>{index + 1}. {action}</li>)}</ol></div>}
            </section>
          )}

          {applyError && <div className="rounded-xl border border-rose-500/20 bg-rose-500/[0.08] p-4 text-sm text-rose-200">{applyError}</div>}
          {run.error && <RunFailureCard error={run.error} onResume={onResume} onDismiss={onDismiss} />}
        </div>

        <aside className="border-t border-white/[0.07] p-5 lg:border-l lg:border-t-0">
          <SectionTitle icon={<TerminalSquare size={15} />} title="Live Activity" />
          <div className="mt-4 max-h-[610px] space-y-1 overflow-auto">
            {events.map((event) => <EventItem key={event.id} event={event} />)}
            {events.length === 0 && <EmptyState text="Noch keine Aktivität." />}
          </div>
        </aside>
      </div>
    </div>
  );
}

function RunFailureCard({ error, onResume, onDismiss }: { error: string; onResume: () => void; onDismiss: () => void }) {
  const modelFailure = /json|ollama|llm|model/i.test(error);
  const repairFailure = /reparatur/i.test(error);
  const help = modelFailure
    ? "Die lokale Modellantwort war unvollständig. Mission Control kann den Run mit kompaktem Kontext und sauberem Workspace erneut starten."
    : repairFailure
      ? "Die automatische Validierung blieb nach den Reparaturrunden rot. Öffne die Activity für den letzten Check oder starte sauber neu."
      : "Der Run wurde sicher gestoppt. Der isolierte Zwischenstand wird beim Fortsetzen verworfen.";
  return <div className="rounded-xl border border-rose-500/20 bg-rose-500/[0.08] p-4"><p className="text-sm font-medium text-rose-200">Run gestoppt</p><p className="mt-1 text-xs leading-5 text-slate-400">{help}</p><code className="mt-2 block rounded-lg bg-black/20 px-3 py-2 text-[11px] text-rose-200/70">{error}</code><div className="mt-3 flex flex-wrap gap-2"><button onClick={onResume} className="mc-button flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-slate-200"><RefreshCw size={13} /> Sauber neu starten</button><button onClick={onDismiss} className="mc-button rounded-lg px-3 py-2 text-xs text-slate-400">Im Verlauf behalten</button></div></div>;
}

function AgentStage({ agent, last }: { agent: AgentProfile; last: boolean }) {
  const active = agent.status === "active";
  const done = agent.status === "completed";
  return (
    <div
      data-testid="agent-stage"
      className={`group relative flex min-w-0 items-center gap-2.5 rounded-2xl border px-3 py-3 transition duration-300 ${active ? "border-cyan-300/25 bg-cyan-300/[0.055] shadow-lg shadow-cyan-500/5" : done ? "border-emerald-300/15 bg-emerald-300/[0.025]" : "border-white/[0.065] bg-black/10 hover:border-white/[0.11] hover:bg-white/[0.025]"}`}
    >
      <span className="relative shrink-0">
        <AgentGlyph id={agent.id} color={agent.color} size="sm" active={active} />
        {done && (
          <span className="absolute -bottom-0.5 -right-0.5 grid h-4 w-4 place-items-center rounded-full border-2 border-[#0e1218] bg-emerald-400 text-[#07100c] shadow-sm shadow-emerald-400/30">
            <Check size={9} strokeWidth={3} />
          </span>
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-medium text-slate-300">{agent.name}</span>
        <span className={`mt-0.5 block truncate text-[10px] ${active ? "text-cyan-300/70" : done ? "text-emerald-300/55" : "text-slate-600"}`}>{AGENT_STATUS_LABELS[agent.status]}</span>
      </span>
      {!last && (
        <span className="absolute -right-2.5 z-10 hidden h-5 w-5 items-center justify-center rounded-full border border-white/[0.07] bg-[#0d1117] text-slate-700 lg:flex">
          <ChevronRight size={11} />
        </span>
      )}
    </div>
  );
}

function EventItem({ event }: { event: RunEvent }) {
  const payload = event.payload as Record<string, unknown> | null;
  const agent = typeof payload?.agent === "string" ? payload.agent : null;
  const tool = typeof payload?.tool === "string" ? payload.tool : null;
  const label = event.type.startsWith("agent.") ? `${agent ?? "Agent"} · ${event.type.split(".")[1]}` : tool ?? event.type.replaceAll(".", " ");
  return (
    <details className="group rounded-lg px-2 py-2.5 hover:bg-white/[0.03]">
      <summary className="flex cursor-pointer list-none items-start gap-2.5">
        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-600 group-open:bg-cyan-300" />
        <span className="min-w-0 flex-1"><span className="block truncate text-xs capitalize text-slate-400">{label}</span><time className="mt-1 block text-[10px] text-slate-700">{new Date(event.created_at).toLocaleTimeString("de-DE")}</time></span>
      </summary>
      <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap border-l border-white/[0.06] pl-4 text-[10px] leading-4 text-slate-600">{JSON.stringify(event.payload, null, 2)}</pre>
    </details>
  );
}

function StatusBadge({ status }: { status: RunStatus }) {
  const tone = toneForStatus(status);
  return <span className={`rounded-md px-2 py-1 font-medium ${badgeTone[tone]}`}>{statusLabel[status]}</span>;
}

function CompactMetric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-xl border border-white/[0.06] bg-black/10 p-3"><p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p><p className="mt-1 text-sm font-medium text-slate-300">{value}</p></div>;
}

function SectionTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{icon}{title}</h3>;
}

function ActionButton({ icon, label, onClick, danger = false }: { icon: React.ReactNode; label: string; onClick: () => void; danger?: boolean }) {
  return <button onClick={onClick} className={`mc-button flex h-9 items-center gap-2 rounded-xl px-3 text-xs font-medium ${danger ? "border-rose-500/20 text-rose-300 hover:bg-rose-500/10" : "text-slate-300"}`}>{icon}{label}</button>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="py-12 text-center"><Bot size={22} className="mx-auto text-slate-700" /><p className="mt-3 text-xs text-slate-600">{text}</p></div>;
}

function PromptChip({ label, onClick }: { label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="mc-button rounded-xl px-2.5 py-1.5 text-[11px] text-slate-500 hover:text-cyan-200">{label}</button>;
}

function NumberField({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return <label><span className="text-[10px] uppercase tracking-wider text-slate-600">{label}</span><input type="number" value={value} min={min} max={max} onChange={(event) => onChange(Number(event.target.value))} className="mt-1.5 w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-3 py-2 text-xs text-slate-300 outline-none focus:border-cyan-300/30" /></label>;
}
