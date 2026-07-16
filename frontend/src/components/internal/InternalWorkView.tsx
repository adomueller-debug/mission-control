import {
  Activity,
  ArrowRight,
  Bot,
  CheckCircle2,
  Clock3,
  Plus,
  Wrench,
  XCircle,
} from "lucide-react";

import type { AgentProfile } from "../../lib/agentTypes";
import type { AgentRun, RunStatus } from "../../lib/runStore";
import { AgentGlyph } from "../agents/AgentGlyph";

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

type Props = {
  runs: AgentRun[];
  agents: AgentProfile[];
  onOpenRun: (runId: string) => void;
  onNewInternal: () => void;
};

export function InternalWorkView({ runs, agents, onOpenRun, onNewInternal }: Props) {
  const internalRuns = runs.filter((run) => run.workstream === "internal");
  const active = internalRuns.filter((run) => !terminal.has(run.status));
  const failed = internalRuns.filter((run) => run.status === "failed");
  const completed = internalRuns.filter((run) => run.status === "completed");
  const successRate = internalRuns.length
    ? Math.round((completed.length / internalRuns.length) * 100)
    : 0;

  return (
    <div className="mc-enter mt-7 space-y-5">
      <section className="mc-glass relative overflow-hidden rounded-[28px] p-5 sm:p-7">
        <div className="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full bg-violet-400/[0.08] blur-3xl" />
        <div className="relative flex flex-wrap items-end justify-between gap-5">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-violet-300/75"><Wrench size={14} /> Interne Organisation</div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight">Mission Control weiterentwickeln</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Dashboard, Agentenlogik, Abläufe und Plattformqualität – getrennt von Kunden- und Business-Projekten, aber mit derselben autonomen Runtime.</p>
          </div>
          <button onClick={onNewInternal} className="mc-button-primary mc-arrow-action flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold"><Plus size={14} /> Interne Aufgabe <ArrowRight size={13} /></button>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <InternalMetric label="Aktiv" value={active.length} detail="Agenten arbeiten" icon={<Activity size={16} />} tone="cyan" />
        <InternalMetric label="Fehlgeschlagen" value={failed.length} detail="prüfbare Runs" icon={<XCircle size={16} />} tone={failed.length ? "rose" : "slate"} />
        <InternalMetric label="Abgeschlossen" value={completed.length} detail="interne Verbesserungen" icon={<CheckCircle2 size={16} />} tone="emerald" />
        <InternalMetric label="Erfolgsquote" value={`${successRate}%`} detail={`${internalRuns.length} interne Runs`} icon={<Clock3 size={16} />} tone="violet" />
      </section>

      {active.length > 0 && (
        <section className="mc-panel rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.025] p-4 sm:p-5">
          <div className="flex items-center gap-2"><span className="h-2 w-2 animate-pulse rounded-full bg-cyan-300" /><h3 className="text-sm font-semibold">Jetzt in Arbeit</h3></div>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">{active.map((run) => <InternalRunCard key={run.id} run={run} agents={agents} onOpen={onOpenRun} />)}</div>
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
          <div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-[0.16em] text-slate-600">Arbeitsverlauf</p><h3 className="mt-1 text-sm font-semibold">Interne Aufgaben</h3></div><span className="text-xs text-slate-600">{internalRuns.length}</span></div>
          <div className="mt-4 space-y-2">{internalRuns.slice(0, 20).map((run) => <InternalRunRow key={run.id} run={run} onOpen={onOpenRun} />)}{internalRuns.length === 0 && <EmptyInternal onCreate={onNewInternal} />}</div>
        </div>
        <aside className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
          <div className="flex items-center gap-2"><Bot size={15} className="text-violet-300" /><h3 className="text-sm font-semibold">Zuständigkeit</h3></div>
          <div className="mt-4 space-y-3 text-xs leading-5 text-slate-500">
            <p><span className="text-slate-300">BOSS</span> priorisiert interne Arbeit.</p>
            <p><span className="text-slate-300">FORGE</span> übernimmt Code, Architektur und Tests.</p>
            <p><span className="text-slate-300">AURA</span> verantwortet Oberfläche und Nutzerführung.</p>
            <p><span className="text-slate-300">SAGE</span> optimiert Agenten, Modelle und Memory.</p>
          </div>
          <div className="mt-5 rounded-xl border border-violet-300/10 bg-violet-300/[0.03] p-3 text-[10px] leading-4 text-slate-600">Interne Runs verändern keine Projekt-KPIs. Validierte Codeänderungen bleiben bis zur Übernahme isoliert.</div>
        </aside>
      </section>
    </div>
  );
}

function InternalRunCard({ run, agents, onOpen }: { run: AgentRun; agents: AgentProfile[]; onOpen: (id: string) => void }) {
  const agent = agents.find((item) => item.id === run.current_step || item.legacy_ids.includes(run.current_step ?? ""));
  return <button onClick={() => onOpen(run.id)} className="mc-arrow-action flex min-w-0 items-center gap-3 rounded-xl border border-white/[0.07] bg-black/10 p-3 text-left hover:border-cyan-300/20"><AgentGlyph id={agent?.id ?? "boss"} color={agent?.color ?? "#67e8f9"} size="sm" active /><span className="min-w-0 flex-1"><span className="block text-[10px] font-semibold uppercase tracking-wider text-cyan-300/70">{agent?.name ?? "BOSS"} · {statusLabel[run.status]}</span><span className="mt-1 block truncate text-xs text-slate-300">{runTitle(run.task)}</span></span><ArrowRight size={13} className="text-slate-600" /></button>;
}

function InternalRunRow({ run, onOpen }: { run: AgentRun; onOpen: (id: string) => void }) {
  const failed = run.status === "failed";
  return <button onClick={() => onOpen(run.id)} className="mc-arrow-action flex w-full items-center gap-3 rounded-xl border border-white/[0.055] bg-black/10 px-3 py-3 text-left hover:border-white/[0.11]"><span className={`h-2 w-2 shrink-0 rounded-full ${failed ? "bg-rose-400" : run.status === "completed" ? "bg-emerald-400" : "animate-pulse bg-cyan-300"}`} /><span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium text-slate-300">{runTitle(run.task)}</span><span className="mt-1 block text-[10px] text-slate-600">{statusLabel[run.status]} · {new Date(run.updated_at).toLocaleString("de-DE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</span></span><ArrowRight size={12} className="text-slate-700" /></button>;
}

function InternalMetric({ label, value, detail, icon, tone }: { label: string; value: string | number; detail: string; icon: React.ReactNode; tone: "slate" | "cyan" | "emerald" | "rose" | "violet" }) {
  const tones = { slate: "text-slate-500", cyan: "text-cyan-300", emerald: "text-emerald-300", rose: "text-rose-300", violet: "text-violet-300" };
  return <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4"><div className={`flex items-center justify-between text-xs ${tones[tone]}`}><span>{label}</span>{icon}</div><p className="mt-3 text-xl font-semibold">{value}</p><p className="mt-1 text-[11px] text-slate-600">{detail}</p></div>;
}

function EmptyInternal({ onCreate }: { onCreate: () => void }) {
  return <div className="rounded-xl border border-dashed border-white/[0.07] px-5 py-10 text-center"><Wrench size={20} className="mx-auto text-slate-700" /><p className="mt-3 text-xs text-slate-500">Noch keine interne Arbeit erfasst.</p><button onClick={onCreate} className="mt-3 text-[11px] text-violet-300">Erste interne Aufgabe anlegen</button></div>;
}

function runTitle(task: string) {
  const first = task.split("\n").find((line) => line.trim())?.trim() ?? "Interne Aufgabe";
  return first.length > 100 ? `${first.slice(0, 97)}…` : first;
}
