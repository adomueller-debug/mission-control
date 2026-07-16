import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Archive,
  ArrowRight,
  Bot,
  BriefcaseBusiness,
  CalendarDays,
  ChevronDown,
  CheckCircle2,
  CircleDollarSign,
  CloudUpload,
  Download,
  ExternalLink,
  Eye,
  FileCode2,
  FileText,
  FolderKanban,
  Globe2,
  ListTodo,
  PackageCheck,
  Pause,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Target,
  TriangleAlert,
  X,
} from "lucide-react";

import type { AgentProfile } from "../../lib/agentTypes";
import { API_BASE, api } from "../../lib/api";
import type {
  Project,
  ProjectStatus,
  ProjectTask,
  ProjectTaskStatus,
  ProjectTaskType,
} from "../../lib/projectTypes";
import { MissionPlanner } from "./MissionPlanner";

const projectStatusLabel: Record<ProjectStatus, string> = {
  idea: "Idee",
  planning: "Planung",
  active: "Aktiv",
  paused: "Pausiert",
  completed: "Abgeschlossen",
  archived: "Archiviert",
};

const taskStatusLabel: Record<ProjectTaskStatus, string> = {
  backlog: "Backlog",
  planned: "Geplant",
  queued: "Wartet",
  in_progress: "In Arbeit",
  blocked: "Blockiert",
  review: "Prüfung",
  completed: "Erledigt",
  cancelled: "Abgebrochen",
};

const taskTypeLabel: Record<ProjectTaskType, string> = {
  general: "Allgemein",
  coding: "Software",
  research: "Recherche",
  design: "Design",
  automation: "Automation",
  business: "Business",
  data: "Daten",
  security: "Security",
  devops: "DevOps",
};

const openStatuses = new Set<ProjectTaskStatus>(["planned", "queued", "in_progress", "blocked", "review"]);
const activeWorkStatuses = new Set<ProjectTaskStatus>(["queued", "in_progress", "review"]);

type Props = {
  agents: AgentProfile[];
  defaultWorkspace: string;
  initialProjectId?: string | null;
  createRequest?: number;
  onOpenRun: (runId: string) => void;
};

export function ProjectPortfolioView({ agents, defaultWorkspace, initialProjectId, createRequest = 0, onOpenRun }: Props) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialProjectId ?? null);
  const [portfolioMode, setPortfolioMode] = useState<"current" | "archived">("current");
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const result = await api<Project[]>("/api/v1/projects");
      setProjects(result);
      if (initialProjectId && result.find((project) => project.id === initialProjectId)?.status === "archived") {
        setPortfolioMode("archived");
      }
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Projekte konnten nicht geladen werden");
    } finally {
      setLoading(false);
    }
  }, [initialProjectId]);

  useEffect(() => {
    const initialTimer = window.setTimeout(() => void load(), 0);
    const timer = window.setInterval(() => void load(), 5000);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(timer);
    };
  }, [load]);

  useEffect(() => {
    if (createRequest <= 0) return;
    const timer = window.setTimeout(() => {
      setPortfolioMode("current");
      setSelectedId(null);
      setShowCreate(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [createRequest]);

  const selected = projects.find((project) => project.id === selectedId) ?? null;
  const currentProjects = projects.filter((project) => project.status !== "archived");
  const archivedProjects = projects.filter((project) => project.status === "archived");
  const visibleProjects = portfolioMode === "archived" ? archivedProjects : currentProjects;
  const operationalTasks = currentProjects.flatMap((project) => project.tasks.map((task) => ({ ...task, projectName: project.name })));
  const activeProjects = currentProjects.filter((project) => ["planning", "active"].includes(project.status)).length;
  const openTasks = operationalTasks.filter((task) => openStatuses.has(task.status)).length;
  const blockedTasks = operationalTasks.filter((task) => task.status === "blocked").length;
  const activeAssignments = operationalTasks.filter((task) => activeWorkStatuses.has(task.status) && task.assigned_agent);

  function switchPortfolio(mode: "current" | "archived") {
    setPortfolioMode(mode);
    setSelectedId(null);
    setShowCreate(false);
  }

  async function createProject(payload: { name: string; goal: string; category: string; owner_agent: string | null; deadline: string | null; budget_cents: number; revenue_target_cents: number }) {
    const project = await api<Project>("/api/v1/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, workspace: defaultWorkspace, status: "planning" }),
    });
    await load();
    setSelectedId(project.id);
    setShowCreate(false);
  }

  async function createTask(payload: {
    title: string;
    description: string;
    task_type: ProjectTaskType;
    assigned_agent: string | null;
    priority: number;
    due_at: string | null;
  }) {
    if (!selected) return;
    await api<ProjectTask>(`/api/v1/projects/${selected.id}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await load();
  }

  async function updateTask(taskId: string, status: ProjectTaskStatus) {
    await api<ProjectTask>(`/api/v1/project-tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    await load();
  }

  async function startTask(taskId: string) {
    const result = await api<{ run: { id: string } }>(`/api/v1/project-tasks/${taskId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    await load();
    onOpenRun(result.run.id);
  }

  async function toggleAutopilot(project: Project) {
    await api<Project>(`/api/v1/projects/${project.id}/autopilot/${project.autopilot_enabled ? "stop" : "start"}`, {
      method: "POST",
    });
    await load();
  }

  return (
    <div className="mc-enter mt-7 space-y-5">
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          <TriangleAlert size={16} /> {error}
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <PortfolioMetric label="Aktuelle Projekte" value={currentProjects.length} detail={`${activeProjects} in Planung oder aktiv`} icon={<FolderKanban size={17} />} />
        <PortfolioMetric label="Offene Aufgaben" value={openTasks} detail="Archivierte Projekte ausgenommen" icon={<ListTodo size={17} />} />
        <PortfolioMetric label="Agenten im Einsatz" value={new Set(activeAssignments.map((task) => task.assigned_agent)).size} detail="projektübergreifend" icon={<Bot size={17} />} />
        <PortfolioMetric label="Blockiert" value={blockedTasks} detail={blockedTasks ? "Handlungsbedarf" : "Keine Blocker"} icon={<TriangleAlert size={17} />} alert={blockedTasks > 0} />
      </section>

      <section className="grid gap-4 2xl:grid-cols-[330px_minmax(0,1fr)_310px]">
        <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3">
          <div className="flex items-center justify-between px-2 py-2">
            <div>
              <p className="text-[10px] uppercase tracking-[0.16em] text-slate-600">Portfolio</p>
              <h2 className="mt-1 text-sm font-semibold">Projekte</h2>
            </div>
            <button onClick={() => setShowCreate((value) => !value)} className="mc-icon-button h-8 w-8 rounded-xl text-slate-400" aria-label="Projekt anlegen">
              <Plus size={16} />
            </button>
          </div>
          <div className="mc-segment mx-2 mt-2 grid grid-cols-2 rounded-xl p-1">
            <button onClick={() => switchPortfolio("current")} className={`rounded-lg px-3 py-2 text-[11px] font-medium ${portfolioMode === "current" ? "mc-segment-active text-slate-200" : "text-slate-600 hover:text-slate-400"}`}>Aktuell <span className="ml-1 text-slate-600">{currentProjects.length}</span></button>
            <button onClick={() => switchPortfolio("archived")} className={`flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-[11px] font-medium ${portfolioMode === "archived" ? "mc-segment-active text-slate-200" : "text-slate-600 hover:text-slate-400"}`}><Archive size={12} /> Archiviert <span className="text-slate-600">{archivedProjects.length}</span></button>
          </div>
          {showCreate && <CreateProjectForm agents={agents.filter((agent) => !agent.specialist)} onSubmit={createProject} />}
          <div className="mt-2 space-y-2">
            {visibleProjects.map((project) => (
              <button key={project.id} onClick={() => setSelectedId(project.id)} className={`group w-full rounded-2xl border p-3 text-left duration-300 ${selected?.id === project.id ? "border-cyan-300/20 bg-cyan-300/[0.055] shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_8px_24px_rgba(0,0,0,0.12)]" : "border-transparent bg-white/[0.018] hover:-translate-y-0.5 hover:border-white/[0.08] hover:bg-white/[0.04] hover:shadow-xl hover:shadow-black/10"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-200">{project.name}</p>
                    <p className="mt-1 text-[11px] capitalize text-slate-600">{project.category} · {projectStatusLabel[project.status]}</p>
                  </div>
                  <span className={`text-xs font-medium ${project.status === "archived" ? "text-slate-600" : "text-cyan-300"}`}>{project.progress}%</span>
                </div>
                <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/[0.06]"><div className={`h-full rounded-full transition-all duration-700 ${project.status === "archived" ? "bg-slate-700" : "bg-cyan-400"}`} style={{ width: `${project.progress}%` }} /></div>
                {project.status === "archived" ? <p className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-700"><Archive size={10} /> Keine aktiven Aufgaben</p> : <div className="mt-2 flex items-center justify-between text-[10px] text-slate-600"><span>{project.tasks.filter((task) => openStatuses.has(task.status)).length} offen</span><span>{project.active_agents.length} Agenten</span></div>}
              </button>
            ))}
            {!loading && visibleProjects.length === 0 && (portfolioMode === "archived" ? <div className="rounded-xl border border-dashed border-white/[0.06] px-4 py-10 text-center"><Archive size={18} className="mx-auto text-slate-700" /><p className="mt-2 text-xs text-slate-600">Noch keine archivierten Projekte</p></div> : <EmptyPortfolio onCreate={() => setShowCreate(true)} />)}
          </div>
        </div>

        <div className="mc-panel min-w-0 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
          {selected ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.07] pb-5">
                <div>
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-cyan-400"><BriefcaseBusiness size={13} /> {selected.category}</div>
                  <h2 className="mt-2 text-xl font-semibold tracking-tight">{selected.name}</h2>
                  <p className="mt-2 line-clamp-3 max-w-2xl text-xs leading-5 text-slate-500">{selected.goal || "Noch kein messbares Projektziel hinterlegt."}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-[10px] text-slate-500">
                    <span className="rounded-lg bg-white/[0.04] px-2 py-1.5">Lead: {agents.find((agent) => agent.id === selected.owner_agent)?.name ?? "Nicht zugewiesen"}</span>
                    <span className="rounded-lg bg-white/[0.04] px-2 py-1.5">Deadline: {selected.deadline ? new Date(selected.deadline).toLocaleDateString("de-DE") : "Offen"}</span>
                    <span className="rounded-lg bg-white/[0.04] px-2 py-1.5">Budget: {(selected.budget_cents / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" })}</span>
                    <span className="rounded-lg bg-white/[0.04] px-2 py-1.5">Umsatzziel: {(selected.revenue_target_cents / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" })}</span>
                  </div>
                  {selected.goal.length > 260 && <details className="mt-2 text-[11px] text-slate-600"><summary className="cursor-pointer text-cyan-300/70">Vollständiges Briefing anzeigen</summary><p className="mt-2 max-w-3xl whitespace-pre-wrap leading-5">{selected.goal}</p></details>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-lg border border-white/[0.07] bg-white/[0.03] px-2.5 py-1.5 text-xs text-slate-400">{projectStatusLabel[selected.status]}</span>
                  <button onClick={() => void toggleAutopilot(selected)} className={`mc-button flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs ${selected.autopilot_enabled ? "text-emerald-300" : "text-slate-500"}`}>
                    {selected.autopilot_enabled ? <Pause size={12} /> : <Play size={12} />} {selected.autopilot_enabled ? "Autopilot aktiv" : selected.tasks.some((task) => task.status === "blocked") ? "Autopilot fortsetzen" : "Autopilot starten"}
                  </button>
                </div>
              </div>
              {selected.status === "archived" ? <><ArchivedProjectSummary project={selected} /><ProjectResults project={selected} agents={agents} onOpenRun={onOpenRun} onRefresh={load} /></> : <>{selected.autopilot_enabled ? <AutopilotStatus project={selected} agents={agents} /> : selected.tasks.length === 0 ? <MissionPlanner key={selected.id} project={selected} agents={agents} onApproved={load} /> : null}<ProjectResults project={selected} agents={agents} onOpenRun={onOpenRun} onRefresh={load} /><TaskBoard project={selected} agents={agents} onCreate={createTask} onUpdate={updateTask} onStart={startTask} onOpenRun={onOpenRun} /></>}
            </>
          ) : (
            <div className="grid min-h-[500px] place-items-center px-6 text-center"><div><FolderKanban size={26} className="mx-auto text-slate-700" /><p className="mt-3 text-sm font-medium text-slate-400">Wähle ein Projekt</p><p className="mt-1 max-w-sm text-xs leading-5 text-slate-600">Details, Briefing und Aufgaben werden erst geöffnet, wenn du ein Projekt auswählst.</p></div></div>
          )}
        </div>

        <AgentWorkload agents={agents} tasks={activeAssignments} />
      </section>
    </div>
  );
}

function AutopilotStatus({ project, agents }: { project: Project; agents: AgentProfile[] }) {
  const current = project.tasks.find((task) => activeWorkStatuses.has(task.status));
  const agent = agents.find((item) => item.id === current?.assigned_agent);
  return <div className="mt-5 flex items-center gap-3 rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.035] p-4"><div className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-300/10 text-emerald-300"><Bot size={16} /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium text-emerald-100">BOSS Autopilot orchestriert dieses Projekt</p><p className="mt-1 truncate text-[11px] text-slate-500">{current ? `${agent?.name ?? current.assigned_agent ?? "Agent"}: ${current.title}` : "Die nächste abhängige Aufgabe wird automatisch gestartet."}</p></div><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" /></div>;
}

function ArchivedProjectSummary({ project }: { project: Project }) {
  const completed = project.tasks.filter((task) => task.status === "completed").length;
  return <div className="mt-5 rounded-2xl border border-white/[0.06] bg-black/10 p-5"><div className="flex items-start gap-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-white/[0.04] text-slate-500"><Archive size={16} /></div><div><p className="text-sm font-medium text-slate-300">Projekt ist archiviert</p><p className="mt-1 text-xs leading-5 text-slate-600">Seine {project.tasks.length} Aufgaben werden nicht als offen gezählt und belegen keine Agenten. {completed} Aufgaben waren beim Archivieren abgeschlossen.</p></div></div><button className="mt-4 flex items-center gap-2 rounded-lg border border-white/[0.07] px-3 py-2 text-[11px] text-slate-500" disabled><RotateCcw size={12} /> Wiederherstellung folgt</button></div>;
}

type ResultArtifact = { title: string; content: string; artifact_type?: string };

function ProjectResults({ project, agents, onOpenRun, onRefresh }: { project: Project; agents: AgentProfile[]; onOpenRun: (id: string) => void; onRefresh: () => Promise<void> }) {
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const results = project.tasks.flatMap((task) => {
    const payload = task.result;
    if (!payload) return [];
    const summary = typeof payload.summary === "string" ? payload.summary : "";
    const files = Array.isArray(payload.files) ? payload.files.filter((item): item is string => typeof item === "string") : [];
    const artifacts = Array.isArray(payload.artifacts) ? payload.artifacts.filter(isResultArtifact) : [];
    const findings = Array.isArray(payload.findings) ? payload.findings.filter((item): item is string => typeof item === "string") : [];
    return [{ task, summary, files, artifacts, findings }];
  });
  const persisted = project.artifacts ?? [];
  if (results.length === 0 && persisted.length === 0) return null;
  const fileCount = results.reduce((total, item) => total + item.files.length, 0);
  const artifactCount = persisted.length || results.reduce((total, item) => total + item.artifacts.length, 0);
  const websites = persisted.filter((artifact) => artifact.preview_available);
  const deliverables = persisted.filter((artifact) => !artifact.preview_available);
  const preview = websites.find((artifact) => artifact.id === previewId);

  async function syncToDrive() {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const response = await api<{ status: string; message?: string }>(`/api/v1/projects/${project.id}/artifacts/sync`, { method: "POST" });
      setSyncMessage(response.message ?? (response.status === "synced" ? "In Google Drive gesichert." : "Lokal gesichert."));
      await onRefresh();
    } catch (reason) {
      setSyncMessage(reason instanceof Error ? reason.message : "Synchronisierung fehlgeschlagen");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <section className="mt-5 rounded-2xl border border-emerald-300/10 bg-emerald-300/[0.02] p-3 sm:p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2"><PackageCheck size={15} className="text-emerald-300" /><div><h3 className="text-sm font-semibold">Ergebnisse & Artefakte</h3><p className="mt-0.5 text-[10px] text-slate-600">Persistiert aus {results.length} abgeschlossenen Agentenaufgaben</p></div></div>
        <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-500"><span className="rounded-lg bg-white/[0.04] px-2 py-1">{fileCount} Dateien</span><span className="rounded-lg bg-white/[0.04] px-2 py-1">{artifactCount} Artefakte</span>{persisted.length > 0 && <button disabled={syncing} onClick={() => void syncToDrive()} className="mc-button flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-cyan-300/80"><CloudUpload size={11} className={syncing ? "animate-pulse" : ""} /> {syncing ? "Synchronisiere…" : "Drive synchronisieren"}</button>}</div>
      </div>
      {syncMessage && <p className="mt-2 rounded-lg bg-white/[0.025] px-3 py-2 text-[10px] text-slate-500">{syncMessage}</p>}
      {websites.length > 0 && <div className="mt-4 grid gap-3 xl:grid-cols-2">{websites.map((artifact) => <article key={artifact.id} className="group overflow-hidden rounded-xl border border-cyan-300/10 bg-black/20"><button onClick={() => setPreviewId(artifact.id)} className="relative block aspect-[16/9] w-full overflow-hidden bg-[#070b10] text-left"><iframe title={artifact.name} src={`${API_BASE}/api/v1/project-artifacts/${artifact.id}/preview`} sandbox="allow-scripts" tabIndex={-1} className="pointer-events-none h-[200%] w-[200%] origin-top-left scale-50 border-0 opacity-80 transition duration-500 group-hover:scale-[0.52] group-hover:opacity-100" /><span className="absolute inset-0 grid place-items-center bg-black/0 transition group-hover:bg-black/25"><span className="flex translate-y-2 items-center gap-2 rounded-full border border-white/10 bg-black/70 px-3 py-2 text-[10px] text-white opacity-0 shadow-2xl backdrop-blur-xl transition group-hover:translate-y-0 group-hover:opacity-100"><Eye size={12} /> Vorschau öffnen</span></span></button><div className="flex items-center gap-3 p-3"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-300/10 text-cyan-300"><Globe2 size={14} /></span><span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium text-slate-300">{artifact.name}</span><span className="mt-0.5 block text-[9px] text-slate-600">Website · {formatBytes(artifact.size_bytes)} · {syncLabel(artifact.sync_status)}</span></span><button onClick={() => setPreviewId(artifact.id)} className="mc-icon-button h-8 w-8 rounded-lg text-slate-400" title="Vorschau öffnen"><Eye size={13} /></button></div></article>)}</div>}
      {deliverables.length > 0 && <div className="mt-3 divide-y divide-white/[0.05] overflow-hidden rounded-xl border border-white/[0.06] bg-black/10">{deliverables.map((artifact) => <div key={artifact.id} className="flex items-center gap-3 px-3 py-2.5"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/[0.04] text-slate-500"><FileText size={13} /></span><span className="min-w-0 flex-1"><span className="block truncate text-[11px] text-slate-300">{artifact.name}</span><span className="mt-0.5 block text-[9px] text-slate-600">{artifact.artifact_type} · {formatBytes(artifact.size_bytes)} · {syncLabel(artifact.sync_status)}</span></span>{artifact.external_url && <a href={artifact.external_url} target="_blank" rel="noreferrer" className="mc-icon-button grid h-8 w-8 place-items-center rounded-lg text-slate-400" title="In Google Drive öffnen"><ExternalLink size={12} /></a>}<a href={`${API_BASE}/api/v1/project-artifacts/${artifact.id}/content`} className="mc-icon-button grid h-8 w-8 place-items-center rounded-lg text-slate-400" title="Herunterladen"><Download size={12} /></a></div>)}</div>}
      <div className="mt-3 grid gap-2 lg:grid-cols-2">
        {results.map(({ task, summary, files, artifacts, findings }) => {
          const agent = agents.find((item) => item.id === task.assigned_agent);
          return (
            <details key={task.id} className="group rounded-xl border border-white/[0.06] bg-black/10 open:border-emerald-300/10">
              <summary className="flex cursor-pointer list-none items-center gap-3 px-3 py-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/[0.04] text-emerald-300"><CheckCircle2 size={14} /></span>
                <span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium text-slate-300">{task.title}</span><span className="mt-1 block text-[9px] text-slate-600">{agent?.name ?? task.assigned_agent ?? "Agent"} · {files.length} Dateien · {artifacts.length} Artefakte</span></span>
                <ChevronDown size={13} className="text-slate-700 transition-transform duration-300 group-open:rotate-180" />
              </summary>
              <div className="border-t border-white/[0.055] px-3 pb-3 pt-3">
                {summary && <p className="text-[11px] leading-5 text-slate-400">{summary}</p>}
                {files.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{files.map((file) => <span key={file} className="flex max-w-full items-center gap-1 rounded-md bg-cyan-300/[0.05] px-2 py-1 text-[9px] text-cyan-200/60"><FileCode2 size={9} /><span className="truncate">{file}</span></span>)}</div>}
                {findings.length > 0 && <ul className="mt-3 space-y-1 text-[10px] leading-4 text-slate-500">{findings.slice(0, 3).map((finding) => <li key={finding}>• {finding}</li>)}</ul>}
                {artifacts.map((artifact) => <details key={artifact.title} className="mt-2 rounded-lg border border-white/[0.05] bg-white/[0.018]"><summary className="cursor-pointer list-none px-2.5 py-2 text-[10px] text-slate-400">{artifact.title}<span className="ml-2 uppercase text-slate-700">{artifact.artifact_type}</span></summary><p className="max-h-48 overflow-auto whitespace-pre-wrap border-t border-white/[0.05] p-2.5 text-[10px] leading-5 text-slate-500">{artifact.content}</p></details>)}
                {task.run_id && <button onClick={() => onOpenRun(task.run_id!)} className="mc-arrow-action mt-3 flex items-center gap-1.5 text-[10px] text-cyan-300/70">Vollständigen Run öffnen <ArrowRight size={11} /></button>}
              </div>
            </details>
          );
        })}
      </div>
      {preview && <div className="fixed inset-0 z-50 grid place-items-center bg-[#030507]/85 p-3 backdrop-blur-xl sm:p-8" role="dialog" aria-modal="true" aria-label={preview.name}><div className="flex h-full max-h-[900px] w-full max-w-[1500px] flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#090d13] shadow-2xl"><div className="flex items-center gap-3 border-b border-white/[0.07] px-4 py-3"><Globe2 size={15} className="text-cyan-300" /><span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-200">{preview.name}</span><a href={`${API_BASE}/api/v1/project-artifacts/${preview.id}/preview`} target="_blank" rel="noreferrer" className="mc-button flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[10px] text-slate-400"><ExternalLink size={11} /> Neuer Tab</a><button onClick={() => setPreviewId(null)} className="mc-icon-button h-8 w-8 rounded-lg text-slate-400" aria-label="Vorschau schließen"><X size={14} /></button></div><iframe title={preview.name} src={`${API_BASE}/api/v1/project-artifacts/${preview.id}/preview`} sandbox="allow-scripts" className="min-h-0 flex-1 border-0 bg-white" /></div></div>}
    </section>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function syncLabel(status: string) {
  if (status === "synced") return "Drive";
  if (status === "pending") return "Drive ausstehend";
  if (status === "failed") return "Sync fehlgeschlagen";
  return "lokal gesichert";
}

function isResultArtifact(value: unknown): value is ResultArtifact {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.title === "string" && typeof candidate.content === "string";
}

function TaskBoard({ project, agents, onCreate, onUpdate, onStart, onOpenRun }: {
  project: Project;
  agents: AgentProfile[];
  onCreate: (payload: { title: string; description: string; task_type: ProjectTaskType; assigned_agent: string | null; priority: number; due_at: string | null }) => Promise<void>;
  onUpdate: (id: string, status: ProjectTaskStatus) => Promise<void>;
  onStart: (id: string) => Promise<void>;
  onOpenRun: (id: string) => void;
}) {
  const [creating, setCreating] = useState(false);
  const groups = useMemo(() => [
    { title: "Backlog", statuses: new Set<ProjectTaskStatus>(["backlog", "planned"]) },
    { title: "In Arbeit", statuses: new Set<ProjectTaskStatus>(["queued", "in_progress", "review", "blocked"]) },
    { title: "Erledigt", statuses: new Set<ProjectTaskStatus>(["completed", "cancelled"]) },
  ], []);

  return (
    <div className="mt-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Aufgabensteuerung</h3>
        <button onClick={() => setCreating((value) => !value)} className="mc-button-primary flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold"><Plus size={14} /> Aufgabe</button>
      </div>
      {creating && <CreateTaskForm agents={agents.filter((agent) => !agent.specialist)} onSubmit={async (payload) => { await onCreate(payload); setCreating(false); }} />}
      <div className="mt-4 grid gap-3 xl:grid-cols-3">
        {groups.map((group) => {
          const tasks = project.tasks.filter((task) => group.statuses.has(task.status));
          return (
            <div key={group.title} className="rounded-xl border border-white/[0.06] bg-black/10 p-2.5">
              <div className="flex items-center justify-between px-1.5 py-1 text-xs font-medium text-slate-400"><span>{group.title}</span><span className="text-slate-700">{tasks.length}</span></div>
              <div className="mt-2 space-y-2">
                {tasks.map((task) => (
                  <TaskCard key={task.id} task={task} agent={agents.find((item) => item.id === task.assigned_agent)} autopilot={project.autopilot_enabled} onUpdate={onUpdate} onStart={onStart} onOpenRun={onOpenRun} />
                ))}
                {tasks.length === 0 && <div className="rounded-lg border border-dashed border-white/[0.06] px-3 py-6 text-center text-[11px] text-slate-700">Keine Aufgaben</div>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TaskCard({ task, agent, autopilot, onUpdate, onStart, onOpenRun }: { task: ProjectTask; agent?: AgentProfile; autopilot: boolean; onUpdate: (id: string, status: ProjectTaskStatus) => Promise<void>; onStart: (id: string) => Promise<void>; onOpenRun: (id: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [now] = useState(() => Date.now());
  const canStart = !autopilot && task.executable && !task.run_id && ["backlog", "planned"].includes(task.status);
  const overdue = task.due_at && new Date(task.due_at).getTime() < now && task.status !== "completed";
  return (
    <article className="rounded-xl border border-white/[0.065] bg-[#0d1219] p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm leading-5 text-slate-300">{task.title}</p>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold ${task.priority === 1 ? "bg-rose-400/10 text-rose-300" : "bg-white/[0.05] text-slate-600"}`}>P{task.priority}</span>
      </div>
      {autopilot && !task.run_id && ["backlog", "planned"].includes(task.status) && <p className="mt-2 text-[9px] text-emerald-300/60">BOSS startet diese Aufgabe automatisch, sobald Abhängigkeiten erfüllt sind.</p>}
      <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[10px]">
        <span className="rounded bg-white/[0.04] px-1.5 py-1 text-slate-500">{taskTypeLabel[task.task_type]}</span>
        <span className="rounded bg-white/[0.04] px-1.5 py-1 text-slate-500">{taskStatusLabel[task.status]}</span>
        {task.due_at && <span className={`flex items-center gap-1 rounded px-1.5 py-1 ${overdue ? "bg-rose-400/10 text-rose-300" : "bg-white/[0.04] text-slate-500"}`}><CalendarDays size={10} />{new Date(task.due_at).toLocaleDateString("de-DE", { day: "2-digit", month: "short" })}</span>}
      </div>
      <div className="mt-3 flex items-center gap-2 border-t border-white/[0.055] pt-2.5">
        <span className="flex min-w-0 items-center gap-1.5 text-[10px] text-slate-600"><Bot size={11} /><span className="truncate">{agent?.name ?? "Nicht zugewiesen"}</span></span>
        <span className="ml-auto flex gap-1">
          {canStart && <button disabled={busy} onClick={() => { setBusy(true); void onStart(task.id).finally(() => setBusy(false)); }} className="mc-icon-button h-7 w-7 rounded-lg text-cyan-300" title="Coding-Run starten">{busy ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} fill="currentColor" />}</button>}
          {task.run_id && <button onClick={() => onOpenRun(task.run_id!)} className="mc-icon-button mc-arrow-action h-7 w-7 rounded-lg text-slate-400" title="Run öffnen"><ArrowRight size={12} /></button>}
          {!task.run_id && task.status !== "completed" && <button onClick={() => void onUpdate(task.id, "completed")} className="mc-icon-button h-7 w-7 rounded-lg text-slate-500 hover:text-emerald-300" title="Als erledigt markieren"><CheckCircle2 size={12} /></button>}
        </span>
      </div>
    </article>
  );
}

function AgentWorkload({ agents, tasks }: { agents: AgentProfile[]; tasks: Array<ProjectTask & { projectName: string }> }) {
  const workload = agents.filter((agent) => !agent.specialist).map((agent) => ({ agent, tasks: tasks.filter((task) => task.assigned_agent === agent.id) })).filter((item) => item.tasks.length > 0);
  return (
    <aside className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
      <div className="flex items-center gap-2"><Bot size={15} className="text-violet-300" /><h2 className="text-sm font-semibold">Aktuelle Arbeit</h2></div>
      <p className="mt-1 text-[11px] leading-5 text-slate-600">Agentenbelegung über alle Projekte</p>
      <div className="mt-4 space-y-3">
        {workload.map(({ agent, tasks: agentTasks }) => (
          <div key={agent.id} className="rounded-xl border border-white/[0.06] bg-black/10 p-3">
            <div className="flex items-center justify-between"><span className="text-xs font-semibold" style={{ color: agent.color }}>{agent.name}</span><span className="text-[10px] text-slate-600">{agentTasks.length} Tasks</span></div>
            <div className="mt-2 space-y-2">{agentTasks.slice(0, 3).map((task) => <div key={task.id}><p className="line-clamp-1 text-[11px] text-slate-400">{task.title}</p><p className="mt-0.5 truncate text-[9px] text-slate-700">{task.projectName} · {taskStatusLabel[task.status]}</p></div>)}</div>
          </div>
        ))}
        {workload.length === 0 && <div className="rounded-xl border border-dashed border-white/[0.07] px-4 py-8 text-center"><Pause size={18} className="mx-auto text-slate-700" /><p className="mt-2 text-xs text-slate-600">Keine Agenten belegt</p></div>}
      </div>
      <div className="mt-4 rounded-xl border border-amber-300/10 bg-amber-300/[0.035] p-3">
        <p className="flex items-center gap-1.5 text-[10px] font-medium text-amber-200/70"><CircleDollarSign size={12} /> Umsatz ist ein Ziel, keine Garantie</p>
        <p className="mt-1.5 text-[10px] leading-4 text-slate-600">Mission Control kann planen und ausführen. Verkauf, Zustimmung und Zahlung bleiben externe Ereignisse.</p>
      </div>
    </aside>
  );
}

function CreateProjectForm({ agents, onSubmit }: { agents: AgentProfile[]; onSubmit: (payload: { name: string; goal: string; category: string; owner_agent: string | null; deadline: string | null; budget_cents: number; revenue_target_cents: number }) => Promise<void> }) {
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [category, setCategory] = useState("business");
  const [ownerAgent, setOwnerAgent] = useState("boss");
  const [deadline, setDeadline] = useState("");
  const [budget, setBudget] = useState(0);
  const [revenueTarget, setRevenueTarget] = useState(0);
  return (
    <form className="mx-1 mt-2 space-y-2 rounded-xl border border-cyan-300/10 bg-cyan-300/[0.025] p-3" onSubmit={(event) => { event.preventDefault(); if (name.trim()) void onSubmit({ name: name.trim(), goal: goal.trim(), category, owner_agent: ownerAgent || null, deadline: deadline ? new Date(`${deadline}T17:00:00`).toISOString() : null, budget_cents: Math.round(budget * 100), revenue_target_cents: Math.round(revenueTarget * 100) }); }}>
      <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Projektname" className="w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-3 py-2 text-xs outline-none focus:border-cyan-300/30" />
      <textarea value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Messbares Ziel" className="min-h-16 w-full resize-none rounded-lg border border-white/[0.07] bg-[#080b10] px-3 py-2 text-xs outline-none focus:border-cyan-300/30" />
      <div className="grid grid-cols-2 gap-2">
        <select value={category} onChange={(event) => setCategory(event.target.value)} className="min-w-0 rounded-lg border border-white/[0.07] bg-[#080b10] px-2 py-2 text-xs text-slate-400"><option value="business">Business</option><option value="software">Software</option><option value="automation">Automation</option><option value="research">Recherche</option><option value="general">Allgemein</option></select>
        <select value={ownerAgent} onChange={(event) => setOwnerAgent(event.target.value)} className="min-w-0 rounded-lg border border-white/[0.07] bg-[#080b10] px-2 py-2 text-xs text-slate-400"><option value="">Lead später wählen</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select>
        <label><span className="mb-1 block text-[9px] text-slate-600">Deadline</span><input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} className="w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-2 py-2 text-xs text-slate-400" /></label>
        <label><span className="mb-1 block text-[9px] text-slate-600">Budget EUR</span><input type="number" min="0" value={budget} onChange={(event) => setBudget(Number(event.target.value))} className="w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-2 py-2 text-xs text-slate-400" /></label>
        <label className="col-span-2"><span className="mb-1 block text-[9px] text-slate-600">Umsatz-KPI EUR</span><input type="number" min="0" value={revenueTarget} onChange={(event) => setRevenueTarget(Number(event.target.value))} className="w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-2 py-2 text-xs text-slate-400" /></label>
      </div>
      <button className="mc-button-primary w-full rounded-xl px-3 py-2 text-xs font-semibold">Projekt anlegen</button>
    </form>
  );
}

function CreateTaskForm({ agents, onSubmit }: { agents: AgentProfile[]; onSubmit: (payload: { title: string; description: string; task_type: ProjectTaskType; assigned_agent: string | null; priority: number; due_at: string | null }) => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [taskType, setTaskType] = useState<ProjectTaskType>("general");
  const [agent, setAgent] = useState("");
  const [priority, setPriority] = useState(3);
  const [dueAt, setDueAt] = useState("");
  return (
    <form className="mt-4 rounded-xl border border-cyan-300/10 bg-cyan-300/[0.025] p-3" onSubmit={(event) => { event.preventDefault(); if (title.trim()) void onSubmit({ title: title.trim(), description: description.trim(), task_type: taskType, assigned_agent: agent || null, priority, due_at: dueAt ? new Date(`${dueAt}T17:00:00`).toISOString() : null }); }}>
      <div className="grid gap-2 md:grid-cols-2"><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Aufgabentitel" className="rounded-lg border border-white/[0.07] bg-[#080b10] px-3 py-2 text-xs outline-none focus:border-cyan-300/30 md:col-span-2" /><textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Ergebnis und Abnahmekriterien" className="min-h-16 resize-none rounded-lg border border-white/[0.07] bg-[#080b10] px-3 py-2 text-xs outline-none focus:border-cyan-300/30 md:col-span-2" /><select value={taskType} onChange={(event) => setTaskType(event.target.value as ProjectTaskType)} className="rounded-lg border border-white/[0.07] bg-[#080b10] px-2 py-2 text-xs text-slate-400">{Object.entries(taskTypeLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><select value={agent} onChange={(event) => setAgent(event.target.value)} className="rounded-lg border border-white/[0.07] bg-[#080b10] px-2 py-2 text-xs text-slate-400"><option value="">Agent später wählen</option>{agents.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.title}</option>)}</select><label className="md:col-span-2"><span className="mb-1.5 flex items-center gap-1.5 text-[10px] text-slate-600"><CalendarDays size={11} /> Fällig am</span><input type="date" value={dueAt} onChange={(event) => setDueAt(event.target.value)} className="w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-3 py-2 text-xs text-slate-400 outline-none focus:border-cyan-300/30" /></label></div>
      <div className="mt-2 flex items-center justify-between"><label className="flex items-center gap-2 text-[10px] text-slate-600">Priorität<select value={priority} onChange={(event) => setPriority(Number(event.target.value))} className="rounded border border-white/[0.07] bg-[#080b10] px-2 py-1 text-xs text-slate-400">{[1, 2, 3, 4, 5].map((value) => <option key={value}>{value}</option>)}</select></label><button className="mc-button-primary rounded-xl px-3 py-2 text-xs font-semibold">Speichern</button></div>
      {taskType !== "coding" && <p className="mt-2 flex items-center gap-1 text-[9px] text-emerald-300/60"><Bot size={10} /> BOSS kann diese Aufgabe automatisch an den passenden Executor übergeben.</p>}
    </form>
  );
}

function PortfolioMetric({ label, value, detail, icon, alert = false }: { label: string; value: number; detail: string; icon: React.ReactNode; alert?: boolean }) {
  return <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4"><div className={`flex items-center justify-between text-xs ${alert ? "text-amber-300" : "text-slate-500"}`}><span>{label}</span>{icon}</div><p className="mt-3 text-xl font-semibold">{value}</p><p className="mt-1 text-[11px] text-slate-600">{detail}</p></div>;
}

function EmptyPortfolio({ onCreate }: { onCreate: () => void }) {
  return <div className="rounded-xl border border-dashed border-white/[0.07] px-4 py-9 text-center"><Target size={20} className="mx-auto text-slate-700" /><p className="mt-3 text-xs text-slate-500">Aus Ideen werden hier steuerbare Projekte.</p><button onClick={onCreate} className="mt-3 text-[11px] text-cyan-400">Erstes Projekt anlegen</button></div>;
}
