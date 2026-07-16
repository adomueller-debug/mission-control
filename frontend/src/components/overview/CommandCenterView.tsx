import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  Bot,
  CalendarDays,
  CheckCircle2,
  CircleGauge,
  Clock3,
  FolderKanban,
  ListChecks,
  Play,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";

import type { AgentProfile } from "../../lib/agentTypes";
import { api } from "../../lib/api";
import type { Integration } from "../../lib/missionTypes";
import type { Project, ProjectTask } from "../../lib/projectTypes";
import type { AgentRun } from "../../lib/runStore";

const openStatuses = new Set(["backlog", "planned", "queued", "in_progress", "blocked", "review"]);

type Props = {
  agents: AgentProfile[];
  runs: AgentRun[];
  backendConnected: boolean;
  healthyServices: number;
  totalServices: number;
  decisionCount: number;
  onNewMission: () => void;
  onProjects: () => void;
  onCreateProject: () => void;
  onIntegrations: () => void;
};

export function CommandCenterView({
  agents,
  runs,
  backendConnected,
  healthyServices,
  totalServices,
  decisionCount,
  onNewMission,
  onProjects,
  onCreateProject,
  onIntegrations,
}: Props) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [portfolio, catalog] = await Promise.all([
        api<Project[]>("/api/v1/projects"),
        api<Integration[]>("/api/v1/integrations"),
      ]);
      setProjects(portfolio);
      setIntegrations(catalog);
      setUpdatedAt(new Date());
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Arbeitsübersicht konnte nicht geladen werden");
    }
  }, []);

  useEffect(() => {
    const initialTimer = window.setTimeout(() => void load(), 0);
    const timer = window.setInterval(() => void load(), 10_000);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(timer);
    };
  }, [load]);

  const currentProjects = projects.filter((project) => project.status !== "archived");
  const openTasks = currentProjects.flatMap((project) => project.tasks
    .filter((task) => openStatuses.has(task.status))
    .map((task) => ({ ...task, projectName: project.name })));
  const blockedTasks = openTasks.filter((task) => task.status === "blocked");
  const executableTasks = openTasks.filter((task) => task.executable);
  const activeRuns = runs.filter((run) => !["completed", "failed", "cancelled"].includes(run.status));
  const readyIntegrations = integrations.filter((integration) => integration.ready).length;
  const activeAgents = agents.filter((agent) => agent.status === "active").length;

  const focusTasks = [...openTasks].sort((a, b) => {
    const stateRank = (task: ProjectTask) => task.status === "blocked" ? 0 : task.status === "in_progress" ? 1 : task.status === "review" ? 2 : 3;
    return stateRank(a) - stateRank(b) || a.priority - b.priority || dueRank(a.due_at) - dueRank(b.due_at);
  }).slice(0, 5);

  const readinessParts = [
    backendConnected ? 20 : 0,
    totalServices > 0 ? Math.round((healthyServices / totalServices) * 15) : 0,
    integrations.length > 0 ? Math.round((readyIntegrations / integrations.length) * 20) : 0,
    currentProjects.length > 0 ? 15 : 0,
    openTasks.length > 0 ? 15 : 0,
    openTasks.length > 0 ? Math.round((executableTasks.length / openTasks.length) * 15) : 0,
  ];
  const readiness = readinessParts.reduce((sum, value) => sum + value, 0);
  const nextAction = getNextAction({ backendConnected, integrations, currentProjects, openTasks, blockedTasks, decisionCount, activeRuns });
  const dateLabel = new Intl.DateTimeFormat("de-DE", { weekday: "long", day: "2-digit", month: "long" }).format(new Date());

  return (
    <div className="mc-enter mt-7 space-y-5">
      {error && <div className="flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"><TriangleAlert size={16} />{error}</div>}

      <section className="mc-glass relative overflow-hidden rounded-[28px] p-5 sm:p-7">
        <div className="pointer-events-none absolute -right-20 -top-28 h-72 w-72 rounded-full bg-cyan-300/[0.07] blur-3xl" />
        <div className="relative flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-medium capitalize text-cyan-300/75"><CalendarDays size={14} />{dateLabel}</div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">Dein Mission Control für heute</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Ein klarer Blick auf Prioritäten, Entscheidungen und Systembereitschaft – bevor du eine neue Mission startest.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={onCreateProject} className="mc-button flex items-center gap-2 rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-300"><FolderKanban size={14} /> Projekt anlegen</button>
            <button onClick={onNewMission} className="mc-button-primary mc-arrow-action flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold"><Sparkles size={14} /> Neue Mission <ArrowRight size={13} /></button>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <OverviewMetric label="Arbeitsbereitschaft" value={`${readiness}%`} detail={readiness >= 85 ? "Für aktuelle Arbeit startklar" : "Arbeitssetup vervollständigen"} icon={<CircleGauge size={17} />} tone={readiness >= 85 ? "emerald" : "cyan"} />
        <OverviewMetric label="Aktive Projekte" value={currentProjects.length} detail={`${openTasks.length} offene Aufgaben`} icon={<FolderKanban size={17} />} />
        <OverviewMetric label="Entscheidungen" value={decisionCount} detail={decisionCount ? "Deine Freigabe benötigt" : "Nichts wartet auf dich"} icon={<CheckCircle2 size={17} />} tone={decisionCount ? "amber" : "emerald"} />
        <OverviewMetric label="Agenten arbeiten" value={activeAgents} detail={`${activeRuns.length} aktive Missionen`} icon={<Bot size={17} />} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
        <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
          <div className="flex items-start justify-between gap-4">
            <div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-400">Next best action</p><h3 className="mt-1 text-lg font-semibold">{nextAction.title}</h3><p className="mt-2 max-w-2xl text-xs leading-5 text-slate-500">{nextAction.detail}</p></div>
            <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${nextAction.urgent ? "bg-amber-300/10 text-amber-300" : "bg-cyan-300/10 text-cyan-300"}`}>{nextAction.urgent ? <TriangleAlert size={18} /> : <Play size={17} />}</div>
          </div>
          <button onClick={nextAction.action === "create-project" ? onCreateProject : nextAction.action === "projects" ? onProjects : nextAction.action === "integrations" ? onIntegrations : onNewMission} className="mc-button-primary mc-arrow-action mt-5 flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold">{nextAction.label}<ArrowRight size={13} /></button>
        </div>

        <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
          <div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-[0.16em] text-slate-600">System & Zugänge</p><h3 className="mt-1 text-sm font-semibold">Operational Readiness</h3></div><ShieldCheck size={17} className={backendConnected ? "text-emerald-400" : "text-rose-400"} /></div>
          <div className="mt-4 space-y-3">
            <ReadinessRow label="Lokale Services" value={`${healthyServices}/${totalServices}`} ready={totalServices > 0 && healthyServices === totalServices} />
            <ReadinessRow label="Integrationen" value={`${readyIntegrations}/${integrations.length}`} ready={integrations.length > 0 && readyIntegrations === integrations.length} />
            <ReadinessRow label="Agent Runtime" value={activeRuns.length ? "Beschäftigt" : "Bereit"} ready={backendConnected} />
            <ReadinessRow label="Direkt ausführbare Tasks" value={openTasks.length ? `${executableTasks.length}/${openTasks.length}` : "Noch keine"} ready={openTasks.length > 0 && executableTasks.length === openTasks.length} />
          </div>
          <button onClick={onIntegrations} className="mc-arrow-action mt-4 flex items-center gap-1.5 text-[11px] font-medium text-cyan-300/75 hover:text-cyan-200">Details prüfen <ArrowRight size={12} /></button>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
          <div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-[0.16em] text-slate-600">Priorisiert</p><h3 className="mt-1 text-sm font-semibold">Heute im Fokus</h3></div><ListChecks size={17} className="text-slate-500" /></div>
          <div className="mt-4 space-y-2">
            {focusTasks.map((task) => <FocusTask key={task.id} task={task} agent={agents.find((agent) => agent.id === task.assigned_agent)} />)}
            {focusTasks.length === 0 && <EmptyFocus onProjects={onProjects} />}
          </div>
        </div>

        <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
          <div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-[0.16em] text-slate-600">Portfolio</p><h3 className="mt-1 text-sm font-semibold">Projektgesundheit</h3></div><FolderKanban size={17} className="text-slate-500" /></div>
          <div className="mt-4 space-y-3">
            {currentProjects.slice(0, 4).map((project) => <ProjectHealth key={project.id} project={project} />)}
            {currentProjects.length === 0 && <p className="rounded-xl border border-dashed border-white/[0.07] px-4 py-8 text-center text-xs leading-5 text-slate-600">Noch kein aktives Projekt. Archivierte Tests beeinflussen diese Ansicht nicht.</p>}
          </div>
          <button onClick={onProjects} className="mc-arrow-action mt-4 flex items-center gap-1.5 text-[11px] font-medium text-cyan-300/75 hover:text-cyan-200">Portfolio öffnen <ArrowRight size={12} /></button>
        </div>
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-3 px-1 text-[10px] text-slate-700">
        <span>Live aus Projects, Runs, Agents, Health und Integrationen</span>
        <span>{updatedAt ? `Aktualisiert ${updatedAt.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}` : "Daten werden geladen"}</span>
      </footer>
    </div>
  );
}

function OverviewMetric({ label, value, detail, icon, tone = "slate" }: { label: string; value: string | number; detail: string; icon: React.ReactNode; tone?: "slate" | "cyan" | "emerald" | "amber" }) {
  const tones = { slate: "text-slate-500", cyan: "text-cyan-300", emerald: "text-emerald-300", amber: "text-amber-300" };
  return <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4"><div className={`flex items-center justify-between text-xs ${tones[tone]}`}><span>{label}</span>{icon}</div><p className="mt-3 text-xl font-semibold tracking-tight text-slate-100">{value}</p><p className="mt-1 text-[11px] text-slate-600">{detail}</p></div>;
}

function ReadinessRow({ label, value, ready }: { label: string; value: string; ready: boolean }) {
  return <div className="flex items-center gap-3"><span className={`h-2 w-2 rounded-full ${ready ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.35)]" : "bg-amber-400"}`} /><span className="flex-1 text-xs text-slate-500">{label}</span><span className="text-xs font-medium text-slate-300">{value}</span></div>;
}

function FocusTask({ task, agent }: { task: ProjectTask & { projectName: string }; agent?: AgentProfile }) {
  const blocked = task.status === "blocked";
  return <div className="flex items-center gap-3 rounded-xl border border-white/[0.055] bg-black/10 px-3 py-3"><span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg text-[10px] font-semibold ${blocked ? "bg-amber-300/10 text-amber-300" : "bg-white/[0.045] text-slate-500"}`}>P{task.priority}</span><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium text-slate-300">{task.title}</p><p className="mt-1 truncate text-[10px] text-slate-600">{task.projectName} · {agent?.name ?? "Nicht zugewiesen"}</p></div><span className={`rounded-md px-2 py-1 text-[9px] ${blocked ? "bg-amber-300/10 text-amber-300" : "bg-white/[0.04] text-slate-600"}`}>{blocked ? "Blockiert" : task.status === "in_progress" ? "In Arbeit" : task.status === "review" ? "Prüfung" : "Geplant"}</span></div>;
}

function EmptyFocus({ onProjects }: { onProjects: () => void }) {
  return <div className="rounded-xl border border-dashed border-white/[0.07] px-5 py-9 text-center"><Clock3 size={19} className="mx-auto text-slate-700" /><p className="mt-3 text-xs font-medium text-slate-500">Noch keine priorisierte Arbeit</p><p className="mt-1 text-[11px] text-slate-700">Lege ein echtes Projekt an und definiere den ersten messbaren Meilenstein.</p><button onClick={onProjects} className="mt-3 text-[11px] font-medium text-cyan-300/80 hover:text-cyan-200">Zu den Projekten</button></div>;
}

function ProjectHealth({ project }: { project: Project }) {
  const blocked = project.tasks.filter((task) => task.status === "blocked").length;
  return <div><div className="flex items-center justify-between gap-3"><div className="min-w-0"><p className="truncate text-xs font-medium text-slate-300">{project.name}</p><p className="mt-0.5 text-[10px] capitalize text-slate-600">{project.status} · {project.tasks.length} Aufgaben</p></div><span className={blocked ? "text-[10px] text-amber-300" : "text-[10px] text-slate-500"}>{blocked ? `${blocked} blockiert` : `${project.progress}%`}</span></div><div className="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.055]"><div className={`h-full rounded-full transition-all duration-700 ${blocked ? "bg-amber-400" : "bg-cyan-400"}`} style={{ width: `${Math.max(project.progress, 3)}%` }} /></div></div>;
}

function dueRank(value: string | null) {
  return value ? new Date(value).getTime() : Number.MAX_SAFE_INTEGER;
}

function getNextAction({ backendConnected, integrations, currentProjects, openTasks, blockedTasks, decisionCount, activeRuns }: { backendConnected: boolean; integrations: Integration[]; currentProjects: Project[]; openTasks: ProjectTask[]; blockedTasks: ProjectTask[]; decisionCount: number; activeRuns: AgentRun[] }) {
  if (!backendConnected) return { title: "Lokale Runtime wiederherstellen", detail: "Backend oder Kernservices sind nicht vollständig erreichbar. Ohne stabile Runtime sollten keine neuen Missionen gestartet werden.", label: "Operations öffnen", action: "operations", urgent: true } as const;
  if (integrations.some((integration) => !integration.ready)) return { title: "Fehlende Integrationen vervollständigen", detail: "Mindestens ein Zugang ist noch nicht bereit. Prüfe zuerst die betroffenen Konten und Secrets.", label: "Integrationen prüfen", action: "integrations", urgent: true } as const;
  if (decisionCount > 0) return { title: `${decisionCount} Agentenergebnis${decisionCount === 1 ? "" : "se"} entscheiden`, detail: "Validierte Änderungen warten auf Übernahme oder können bewusst im Verlauf behalten werden.", label: "Entscheidungen öffnen", action: "operations", urgent: true } as const;
  if (blockedTasks.length > 0) return { title: "Blockierte Aufgabe auflösen", detail: "Blocker haben Vorrang vor neuer Arbeit. Öffne das Portfolio und entscheide über Ursache, Verantwortlichen und nächsten Schritt.", label: "Blocker öffnen", action: "projects", urgent: true } as const;
  if (currentProjects.length === 0) return { title: "Erstes echtes Projekt anlegen", detail: "Die technischen Tests sind archiviert. Definiere jetzt ein reales Ziel, einen messbaren Erfolg und den ersten Meilenstein.", label: "Projekt anlegen", action: "create-project", urgent: false } as const;
  if (openTasks.length === 0) return { title: "Nächsten Meilenstein planen", detail: "Dein Portfolio hat aktuell keine offene Arbeit. Lege die nächste priorisierte Aufgabe mit Verantwortlichem und Abnahmekriterium an.", label: "Aufgaben planen", action: "projects", urgent: false } as const;
  if (activeRuns.length > 0) return { title: "Laufende Mission beobachten", detail: "Das Agententeam arbeitet bereits. Prüfe nur Fortschritt und Blocker; ein Eingriff ist momentan nicht erforderlich.", label: "Operations öffnen", action: "operations", urgent: false } as const;
  if (openTasks.every((task) => !task.executable)) return { title: "Ausführungspfad für Aufgaben wählen", detail: "Die geplanten Nicht-Coding-Aufgaben sind noch nicht direkt aus dem Projektboard ausführbar. Starte sie als Business-Mission über Operations oder ergänze den passenden Executor.", label: "Operations öffnen", action: "operations", urgent: true } as const;
  return { title: "Höchste Priorität ausführen", detail: "Das System ist bereit und geplante Arbeit liegt vor. Starte die wichtigste Aufgabe oder formuliere die nächste Mission für BOSS.", label: "Mission formulieren", action: "operations", urgent: false } as const;
}
