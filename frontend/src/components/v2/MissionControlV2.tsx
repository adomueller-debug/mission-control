import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  Coins,
  GitBranch,
  Layers3,
  PauseCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import { AgentGlyph } from "../agents/AgentGlyph";
import { api, missionSocketUrl } from "../../lib/api";
import {
  boundedProgress,
  collectionItems,
  normalizeApproval,
  normalizeBudget,
  normalizeMission,
  type ApprovalV2,
  type AgentAssignmentV2,
  type BudgetV2,
  type CreateMissionV2,
  type MissionCollection,
  type MissionStatus,
  type MissionV2,
  type QualityGateV2,
  type RiskLevel,
  type WorkItemStatus,
  type WorkItemV2,
} from "../../lib/missionV2Types";

type LoadState = "loading" | "ready" | "unavailable";

const missionLabels: Record<MissionStatus, string> = {
  draft: "Entwurf",
  planning: "BOSS plant",
  ready: "Bereit",
  running: "In Arbeit",
  waiting_approval: "Freigabe nötig",
  blocked: "Blockiert",
  validating: "Qualitätsprüfung",
  completed: "Abgeschlossen",
  failed: "Fehlgeschlagen",
  cancelled: "Abgebrochen",
};

const workLabels: Record<WorkItemStatus, string> = {
  queued: "Wartet",
  ready: "Bereit",
  active: "Aktiv",
  review: "Im Review",
  retrying: "Reparatur",
  completed: "Fertig",
  skipped: "Übersprungen",
  blocked: "Blockiert",
};

const activeMissionStatuses = new Set<MissionStatus>(["planning", "ready", "running", "waiting_approval", "blocked", "validating"]);

export function MissionControlV2() {
  const [missions, setMissions] = useState<MissionV2[]>([]);
  const [approvals, setApprovals] = useState<ApprovalV2[]>([]);
  const [budget, setBudget] = useState<BudgetV2 | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [composerOpen, setComposerOpen] = useState(false);
  const [busyApproval, setBusyApproval] = useState<string | null>(null);

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setState("loading");
    const [missionResult, approvalResult, budgetResult] = await Promise.allSettled([
      api<MissionV2[] | MissionCollection<MissionV2>>("/api/v2/missions"),
      api<ApprovalV2[] | MissionCollection<ApprovalV2>>("/api/v2/approvals?status=pending"),
      api<BudgetV2 | MissionCollection<BudgetV2>>("/api/v2/budgets"),
    ]);
    if (missionResult.status === "rejected") {
      setState("unavailable");
      setError("Mission Engine V2 ist noch nicht erreichbar. Bestehende Operations funktionieren weiterhin.");
      return;
    }
    let loadedMissions = collectionItems(missionResult.value).map(normalizeMission);
    const preferredId = selectedId && loadedMissions.some((mission) => mission.id === selectedId) ? selectedId : loadedMissions[0]?.id ?? null;
    if (preferredId) {
      const [detailResult, assignmentResult] = await Promise.allSettled([
        api<MissionV2>(`/api/v2/missions/${preferredId}`),
        api<AgentAssignmentV2[] | MissionCollection<AgentAssignmentV2>>(`/api/v2/missions/${preferredId}/assignments`),
      ]);
      if (detailResult.status === "fulfilled") {
        const detail = normalizeMission(detailResult.value);
        if (assignmentResult.status === "fulfilled") detail.assignments = collectionItems(assignmentResult.value);
        loadedMissions = loadedMissions.map((mission) => mission.id === detail.id ? detail : mission);
      }
    }
    setMissions(loadedMissions);
    setSelectedId(preferredId);
    setApprovals(approvalResult.status === "fulfilled" ? collectionItems(approvalResult.value).map(normalizeApproval) : []);
    if (budgetResult.status === "fulfilled") {
      const rawBudget = Array.isArray(budgetResult.value) || "items" in budgetResult.value ? collectionItems(budgetResult.value)[0] : budgetResult.value;
      setBudget(rawBudget ? normalizeBudget(rawBudget) : null);
    }
    setError(null);
    setState("ready");
  }, [selectedId]);

  useEffect(() => {
    const initial = window.setTimeout(() => void load(), 0);
    const timer = window.setInterval(() => void load(true), 5000);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [load]);

  useEffect(() => {
    if (!selectedId) return;
    const socket = new WebSocket(missionSocketUrl(selectedId));
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { mission?: MissionV2 };
        if (!payload.mission) return;
        const live = normalizeMission(payload.mission);
        setMissions((current) => current.map((mission) => mission.id === live.id ? live : mission));
      } catch {
        // The five-second fallback polling remains active after malformed frames.
      }
    };
    return () => socket.close();
  }, [selectedId]);

  const selected = missions.find((mission) => mission.id === selectedId) ?? null;
  const activeMissions = missions.filter((mission) => activeMissionStatuses.has(mission.status));
  const activeAssignments = missions.flatMap((mission) => mission.assignments ?? []).filter((assignment) => assignment.status === "active" || assignment.status === "review" || assignment.status === "retrying");
  const pendingApprovals = approvals.filter((approval) => approval.status === "pending");
  const requiredGates = missions.flatMap((mission) => mission.quality_gates ?? []).filter((gate) => gate.required);
  const passedGates = requiredGates.filter((gate) => gate.status === "passed").length;

  async function decideApproval(id: string, decision: "approve" | "reject") {
    setBusyApproval(id);
    setError(null);
    try {
      await api(`/api/v2/approvals/${id}/${decision}`, { method: "POST" });
      await load(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Freigabe konnte nicht verarbeitet werden.");
    } finally {
      setBusyApproval(null);
    }
  }

  return (
    <div className="mc-enter mt-7 space-y-4">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-300/70"><Sparkles size={13} /> Mission Engine 2.0</div>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">BOSS Command Center</h2>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-500">Ziele delegieren, parallele Agentenarbeit beobachten und externe Aktionen kontrolliert freigeben.</p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => void load()} className="mc-icon-button h-10 w-10 rounded-xl text-slate-400" title="Aktualisieren"><RefreshCw size={15} className={state === "loading" ? "animate-spin" : ""} /></button>
          <button type="button" onClick={() => setComposerOpen((current) => !current)} className="mc-button-primary flex h-10 items-center gap-2 rounded-xl px-4 text-xs font-semibold"><Sparkles size={14} /> Neue Mission</button>
        </div>
      </section>

      {composerOpen && <MissionComposer onClose={() => setComposerOpen(false)} onCreated={(mission) => { setComposerOpen(false); void load(true); setSelectedId(mission.id); }} />}
      {error && <div className="flex items-center gap-3 rounded-xl border border-amber-300/15 bg-amber-300/[0.045] px-4 py-3 text-xs text-amber-100"><AlertTriangle size={15} /><span className="flex-1">{error}</span>{state === "unavailable" && <button type="button" onClick={() => void load()} className="text-amber-200 underline decoration-amber-300/30 underline-offset-4">Erneut prüfen</button>}</div>}

      <section className="grid grid-cols-2 gap-3 xl:grid-cols-5">
        <CommandMetric label="Aktive Missionen" value={activeMissions.length} detail={activeMissions.length ? "BOSS orchestriert" : "Bereit für ein Ziel"} icon={<Activity size={16} />} tone="cyan" />
        <CommandMetric label="Agenten im Einsatz" value={activeAssignments.length} detail="Echte Zuweisungen" icon={<Bot size={16} />} tone="violet" />
        <CommandMetric label="Freigaben" value={pendingApprovals.length} detail={pendingApprovals.length ? "Aktion erforderlich" : "Keine Außenwirkung offen"} icon={<ShieldCheck size={16} />} tone={pendingApprovals.length ? "amber" : "emerald"} />
        <CommandMetric label="Quality Gates" value={requiredGates.length ? `${passedGates}/${requiredGates.length}` : "—"} detail="Erforderlich bestanden" icon={<CheckCircle2 size={16} />} tone="emerald" />
        <BudgetMetric budget={budget} />
      </section>

      {state === "unavailable" ? <UnavailableState onCompose={() => setComposerOpen(true)} /> : (
        <section className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
          <MissionList missions={missions} selectedId={selectedId} onSelect={setSelectedId} />
          <MissionWorkspace mission={selected} />
          <ApprovalInbox approvals={pendingApprovals} busyId={busyApproval} onDecision={(id, decision) => void decideApproval(id, decision)} />
        </section>
      )}
    </div>
  );
}

function MissionComposer({ onClose, onCreated }: { onClose: () => void; onCreated: (mission: MissionV2) => void }) {
  const [goal, setGoal] = useState("");
  const [deadline, setDeadline] = useState("");
  const [budgetEuros, setBudgetEuros] = useState("0");
  const [autonomy, setAutonomy] = useState<RiskLevel>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!goal.trim()) return;
    setBusy(true);
    setError(null);
    const payload: CreateMissionV2 = {
      goal: goal.trim(),
      deadline: deadline ? new Date(deadline).toISOString() : null,
      budget_cents: Math.max(0, Math.round(Number(budgetEuros || 0) * 100)),
      autonomy_level: autonomy,
    };
    try {
      onCreated(normalizeMission(await api<MissionV2>("/api/v2/missions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Mission konnte nicht gestartet werden.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mc-glass overflow-hidden rounded-[22px]">
      <div className="flex items-center justify-between border-b border-white/[0.07] px-5 py-4"><div><p className="text-sm font-semibold">Ziel an BOSS übergeben</p><p className="mt-1 text-[11px] text-slate-600">BOSS erstellt Abhängigkeiten, Agentenaufträge und messbare Abnahmekriterien.</p></div><button type="button" onClick={onClose} className="mc-icon-button h-8 w-8 rounded-lg text-slate-500"><X size={14} /></button></div>
      <div className="p-5">
        <textarea value={goal} onChange={(event) => setGoal(event.target.value)} onKeyDown={(event) => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void submit(); }} autoFocus placeholder="Beschreibe das gewünschte Ergebnis – nicht jeden einzelnen Arbeitsschritt …" className="min-h-24 w-full resize-y bg-transparent text-base leading-6 text-slate-100 outline-none placeholder:text-slate-700" />
        <div className="mt-4 grid gap-3 border-t border-white/[0.07] pt-4 sm:grid-cols-3">
          <label className="text-[10px] uppercase tracking-wider text-slate-600">Deadline<input type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} className="mt-1.5 w-full rounded-xl border border-white/[0.07] bg-black/20 px-3 py-2.5 text-xs normal-case tracking-normal text-slate-300 outline-none" /></label>
          <label className="text-[10px] uppercase tracking-wider text-slate-600">Missionsbudget (€)<input type="number" min="0" step="1" value={budgetEuros} onChange={(event) => setBudgetEuros(event.target.value)} className="mt-1.5 w-full rounded-xl border border-white/[0.07] bg-black/20 px-3 py-2.5 text-xs normal-case tracking-normal text-slate-300 outline-none" /></label>
          <label className="text-[10px] uppercase tracking-wider text-slate-600">Autonomie<select value={autonomy} onChange={(event) => setAutonomy(Number(event.target.value) as RiskLevel)} className="mt-1.5 w-full rounded-xl border border-white/[0.07] bg-[#0b0f15] px-3 py-2.5 text-xs normal-case tracking-normal text-slate-300 outline-none"><option value={0}>Lokal & Entwürfe</option><option value={1}>Autonom protokolliert</option><option value={2}>Außenwirkung freigeben</option><option value={3}>Finanzen einzeln freigeben</option></select></label>
        </div>
        {error && <p className="mt-3 text-xs text-rose-300">{error}</p>}
        <div className="mt-4 flex items-center justify-between gap-3"><p className="text-[10px] text-slate-600">Versand, Veröffentlichung und Käufe werden unabhängig von dieser Auswahl sicher freigegeben.</p><button type="button" onClick={() => void submit()} disabled={busy || !goal.trim()} className="mc-button-primary flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold disabled:opacity-40">{busy ? <RefreshCw size={14} className="animate-spin" /> : <Play size={13} fill="currentColor" />} Mission starten</button></div>
      </div>
    </section>
  );
}

function MissionList({ missions, selectedId, onSelect }: { missions: MissionV2[]; selectedId: string | null; onSelect: (id: string) => void }) {
  return <section className="mc-panel min-h-[600px] rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3"><div className="flex items-center justify-between px-2 py-2"><h3 className="text-sm font-semibold">Missionen</h3><span className="text-[11px] text-slate-600">{missions.length}</span></div><div className="mt-2 space-y-1">{missions.map((mission) => <button key={mission.id} type="button" onClick={() => onSelect(mission.id)} className={`group w-full rounded-xl border p-3 text-left ${selectedId === mission.id ? "border-cyan-300/20 bg-cyan-300/[0.055]" : "border-transparent hover:bg-white/[0.035]"}`}><div className="flex items-start gap-2"><MissionDot status={mission.status} /><div className="min-w-0 flex-1"><p className="line-clamp-2 text-xs font-medium leading-5 text-slate-300">{mission.title || mission.goal}</p><div className="mt-2 flex items-center justify-between text-[10px] text-slate-600"><span>{missionLabels[mission.status]}</span><span>{missionProgress(mission)}%</span></div><Progress value={missionProgress(mission)} /></div><ChevronRight size={13} className="mt-1 text-slate-700 transition group-hover:translate-x-0.5 group-hover:text-slate-500" /></div></button>)}{!missions.length && <div className="grid min-h-48 place-items-center rounded-xl border border-dashed border-white/[0.07] text-center"><div><Layers3 size={21} className="mx-auto text-slate-700" /><p className="mt-3 text-xs text-slate-600">Noch keine V2-Mission.</p></div></div>}</div></section>;
}

function MissionWorkspace({ mission }: { mission: MissionV2 | null }) {
  const workItems = mission?.work_items ?? [];
  const gates = mission?.quality_gates ?? [];
  const activeItems = workItems.filter((item) => item.status === "active" || item.status === "review" || item.status === "retrying");
  if (!mission) return <section className="mc-panel grid min-h-[600px] place-items-center rounded-2xl border border-white/[0.07] bg-white/[0.025]"><div className="text-center"><GitBranch size={24} className="mx-auto text-slate-700" /><p className="mt-3 text-xs text-slate-600">Wähle eine Mission, um ihren Arbeitsgraphen zu sehen.</p></div></section>;
  return <section className="mc-panel min-w-0 rounded-2xl border border-white/[0.07] bg-white/[0.025]"><div className="border-b border-white/[0.07] p-5"><div className="flex flex-wrap items-center gap-2"><StatusPill status={mission.status} /><span className="text-[10px] text-slate-600">#{mission.id.slice(0, 8)}</span><span className="ml-auto text-[11px] font-medium text-cyan-300">{missionProgress(mission)}%</span></div><h3 className="mt-3 text-base font-semibold leading-6">{mission.title || mission.goal}</h3>{mission.title && <details className="mt-2"><summary className="cursor-pointer text-[11px] text-slate-600">Vollständiges Ziel anzeigen</summary><p className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-500">{mission.goal}</p></details>}<div className="mt-4"><Progress value={missionProgress(mission)} large /></div><div className="mt-3 flex flex-wrap gap-2 text-[10px] text-slate-500"><Meta label="Risiko" value={`Stufe ${mission.risk_level}`} /><Meta label="Budget" value={euro(mission.budget_cents ?? 0)} />{mission.deadline && <Meta label="Deadline" value={new Date(mission.deadline).toLocaleDateString("de-DE")} />}</div></div>
    <div className="space-y-6 p-5">
      <section><SectionHeading icon={<Activity size={14} />} title="Parallele Agentenarbeit" detail={activeItems.length ? `${activeItems.length} gleichzeitig aktiv` : "Momentan keine Ausführung"} /><div className="mt-3 grid gap-2 md:grid-cols-2">{activeItems.map((item) => <ActiveAssignment key={item.id} item={item} />)}{!activeItems.length && <CompactEmpty text="BOSS startet bereite Arbeitspakete automatisch." />}</div></section>
      <section><SectionHeading icon={<GitBranch size={14} />} title="Arbeitsgraph" detail={`${workItems.length} Arbeitspakete`} /><WorkGraph items={workItems} /></section>
      <section><SectionHeading icon={<ShieldCheck size={14} />} title="Quality Gates" detail={`${gates.filter((gate) => gate.status === "passed").length}/${gates.length} bestanden`} /><QualityGates gates={gates} /></section>
    </div>
  </section>;
}

function WorkGraph({ items }: { items: WorkItemV2[] }) {
  if (!items.length) return <div className="mt-3"><CompactEmpty text="BOSS erstellt gerade den ausführbaren Missionsplan." /></div>;
  const levels = graphLevels(items);
  return <div className="mt-3 overflow-x-auto pb-2"><div className="flex min-w-max items-start gap-5">{levels.map((level, index) => <div key={index} className="w-56 space-y-2"><p className="px-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-700">Phase {index + 1}</p>{level.map((item) => <WorkCard key={item.id} item={item} />)}</div>)}</div></div>;
}

function WorkCard({ item }: { item: WorkItemV2 }) {
  const active = item.status === "active" || item.status === "review" || item.status === "retrying";
  const progress = workProgress(item);
  return <div className={`rounded-xl border p-3 ${active ? "border-cyan-300/20 bg-cyan-300/[0.04]" : item.status === "blocked" ? "border-rose-300/15 bg-rose-300/[0.035]" : "border-white/[0.06] bg-black/10"}`}><div className="flex items-center gap-2"><AgentGlyph id={item.assigned_agent.toLowerCase()} color={agentColor(item.assigned_agent)} size="sm" active={active} /><div className="min-w-0"><p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">{item.assigned_agent}</p><p className="mt-0.5 truncate text-xs text-slate-300">{item.title}</p></div></div><div className="mt-3 flex items-center justify-between text-[9px] text-slate-600"><span>{workLabels[item.status]}</span><span>{progress}%</span></div><Progress value={progress} />{item.status === "skipped" && <p className="mt-2 text-[10px] leading-4 text-amber-200/65">{item.skip_reason || "Überspringen wurde nicht begründet."}</p>}{item.blocker && <p className="mt-2 text-[10px] leading-4 text-rose-200/65">{item.blocker}</p>}</div>;
}

function ActiveAssignment({ item }: { item: WorkItemV2 }) {
  const progress = workProgress(item);
  return <div className="rounded-xl border border-cyan-300/10 bg-cyan-300/[0.025] p-3"><div className="flex items-center gap-3"><AgentGlyph id={item.assigned_agent.toLowerCase()} color={agentColor(item.assigned_agent)} size="sm" active /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300/70">{item.assigned_agent}</p><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300" /></div><p className="mt-1 truncate text-xs text-slate-300">{item.title}</p></div><span className="text-[10px] text-cyan-300">{progress}%</span></div><div className="mt-3"><Progress value={progress} /></div></div>;
}

function workProgress(item: WorkItemV2) {
  if (item.status === "completed" || item.status === "skipped") return 100;
  return boundedProgress(item.progress);
}

function QualityGates({ gates }: { gates: QualityGateV2[] }) {
  if (!gates.length) return <div className="mt-3"><CompactEmpty text="Quality Gates erscheinen nach der Missionsplanung." /></div>;
  return <div className="mt-3 grid gap-2 sm:grid-cols-2">{gates.map((gate) => <div key={gate.id} className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-black/10 px-3 py-2.5"><GateIcon status={gate.status} /><div className="min-w-0 flex-1"><p className="truncate text-xs text-slate-300">{gate.name}</p><p className="mt-0.5 truncate text-[10px] text-slate-600">{gate.summary || (gate.required ? "Erforderlich" : "Optional")}</p></div></div>)}</div>;
}

function ApprovalInbox({ approvals, busyId, onDecision }: { approvals: ApprovalV2[]; busyId: string | null; onDecision: (id: string, decision: "approve" | "reject") => void }) {
  return <section className="mc-panel min-h-[600px] rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3"><div className="flex items-center justify-between px-2 py-2"><div><h3 className="text-sm font-semibold">Freigabe-Inbox</h3><p className="mt-1 text-[10px] text-slate-600">Externe Auswirkungen</p></div><span className={`grid h-7 min-w-7 place-items-center rounded-lg text-[11px] ${approvals.length ? "bg-amber-300/10 text-amber-200" : "bg-emerald-300/10 text-emerald-300"}`}>{approvals.length}</span></div><div className="mt-2 space-y-2">{approvals.map((approval) => <div key={approval.id} className="rounded-xl border border-amber-300/12 bg-amber-300/[0.025] p-3"><div className="flex items-center gap-2 text-[9px] font-semibold uppercase tracking-wider text-amber-200/70"><ShieldCheck size={12} /> Risiko {approval.risk_level} · {approval.action_type}</div><p className="mt-2 text-xs font-medium leading-5 text-slate-300">{approval.title}</p>{approval.description && <p className="mt-1 line-clamp-3 text-[10px] leading-4 text-slate-600">{approval.description}</p>}<div className="mt-2 space-y-1 text-[10px] text-slate-500">{approval.target && <p>Ziel: <span className="text-slate-400">{approval.target}</span></p>}{approval.amount_cents != null && <p>Betrag: <span className="text-slate-400">{euro(approval.amount_cents)}</span></p>}</div><div className="mt-3 grid grid-cols-2 gap-2"><button type="button" disabled={busyId === approval.id} onClick={() => onDecision(approval.id, "reject")} className="mc-button rounded-lg py-2 text-[10px] text-slate-400 disabled:opacity-40">Ablehnen</button><button type="button" disabled={busyId === approval.id} onClick={() => onDecision(approval.id, "approve")} className="mc-button-primary flex items-center justify-center gap-1.5 rounded-lg py-2 text-[10px] font-semibold disabled:opacity-40">{busyId === approval.id ? <RefreshCw size={11} className="animate-spin" /> : <Check size={11} />} Freigeben</button></div></div>)}{!approvals.length && <div className="grid min-h-48 place-items-center rounded-xl border border-dashed border-white/[0.07] text-center"><div><CheckCircle2 size={22} className="mx-auto text-emerald-400/35" /><p className="mt-3 text-xs text-slate-500">Keine Freigabe offen.</p><p className="mt-1 text-[10px] text-slate-700">Autonome Arbeit läuft im Hintergrund.</p></div></div>}</div></section>;
}

function CommandMetric({ label, value, detail, icon, tone }: { label: string; value: string | number; detail: string; icon: React.ReactNode; tone: "cyan" | "violet" | "amber" | "emerald" }) {
  const colors = { cyan: "text-cyan-300", violet: "text-violet-300", amber: "text-amber-300", emerald: "text-emerald-300" };
  return <div className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4"><div className="flex items-center justify-between text-[11px] text-slate-500"><span>{label}</span><span className={colors[tone]}>{icon}</span></div><p className="mt-3 text-xl font-semibold tracking-tight">{value}</p><p className="mt-1 truncate text-[10px] text-slate-600">{detail}</p></div>;
}

function BudgetMetric({ budget }: { budget: BudgetV2 | null }) {
  const total = budget?.limit_cents ?? 2000;
  const used = (budget?.spent_cents ?? 0) + (budget?.reserved_cents ?? 0);
  const progress = total ? Math.round((used / total) * 100) : 0;
  return <div className="mc-panel col-span-2 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 xl:col-span-1"><div className="flex items-center justify-between text-[11px] text-slate-500"><span>Monatsbudget</span><Coins size={16} className="text-amber-300" /></div><div className="mt-3 flex items-baseline justify-between"><p className="text-xl font-semibold">{euro(used)}</p><span className="text-[10px] text-slate-600">von {euro(total)}</span></div><Progress value={progress} /></div>;
}

function UnavailableState({ onCompose }: { onCompose: () => void }) {
  return <section className="mc-panel grid min-h-[420px] place-items-center rounded-2xl border border-white/[0.07] bg-white/[0.025] px-6 text-center"><div className="max-w-md"><PauseCircle size={30} className="mx-auto text-amber-300/50" /><h3 className="mt-4 text-sm font-semibold">V2-Oberfläche ist vorbereitet</h3><p className="mt-2 text-xs leading-5 text-slate-500">Sobald die neue Mission Engine läuft, erscheinen hier DAG, parallele Agenten, Freigaben und Qualitätsprüfungen. Die vorhandenen Operations bleiben unverändert nutzbar.</p><button type="button" onClick={onCompose} className="mc-button mt-5 inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs text-slate-300">Mission vorbereiten <ArrowRight size={13} /></button></div></section>;
}

function SectionHeading({ icon, title, detail }: { icon: React.ReactNode; title: string; detail: string }) { return <div className="flex items-center gap-2"><span className="text-cyan-300/70">{icon}</span><h4 className="text-xs font-semibold text-slate-300">{title}</h4><span className="ml-auto text-[10px] text-slate-600">{detail}</span></div>; }
function CompactEmpty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed border-white/[0.07] px-4 py-5 text-center text-[11px] text-slate-600">{text}</div>; }
function Meta({ label, value }: { label: string; value: string }) { return <span className="rounded-lg bg-white/[0.04] px-2 py-1"><span className="text-slate-700">{label}</span> · {value}</span>; }
function Progress({ value, large = false }: { value: number; large?: boolean }) { return <div className={`mt-2 overflow-hidden rounded-full bg-white/[0.055] ${large ? "h-1.5" : "h-1"}`}><div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-300 transition-[width] duration-700" style={{ width: `${boundedProgress(value)}%` }} /></div>; }
function MissionDot({ status }: { status: MissionStatus }) { const color = status === "completed" ? "bg-emerald-400" : status === "failed" || status === "blocked" ? "bg-rose-400" : status === "waiting_approval" ? "bg-amber-300" : status === "cancelled" || status === "draft" ? "bg-slate-600" : "bg-cyan-300"; return <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${color} ${activeMissionStatuses.has(status) && status !== "blocked" && status !== "waiting_approval" ? "animate-pulse" : ""}`} />; }
function StatusPill({ status }: { status: MissionStatus }) { return <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.07] bg-white/[0.04] px-2.5 py-1 text-[10px] text-slate-400"><MissionDot status={status} />{missionLabels[status]}</span>; }
function GateIcon({ status }: { status: QualityGateV2["status"] }) { if (status === "passed") return <CheckCircle2 size={15} className="shrink-0 text-emerald-400" />; if (status === "failed") return <AlertTriangle size={15} className="shrink-0 text-rose-400" />; if (status === "running") return <RefreshCw size={15} className="shrink-0 animate-spin text-cyan-300" />; return <CircleDashed size={15} className="shrink-0 text-slate-600" />; }
function missionProgress(mission: MissionV2) { if (mission.progress != null) return boundedProgress(mission.progress); const items = mission.work_items ?? []; if (!items.length) return mission.status === "completed" ? 100 : 0; return Math.round(items.reduce((total, item) => total + (item.status === "completed" ? 100 : boundedProgress(item.progress)), 0) / items.length); }
function euro(cents: number) { return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(cents / 100); }
function agentColor(agent: string) { const colors: Record<string, string> = { BOSS: "#facc15", FORGE: "#fb923c", BLUEPRINT: "#60a5fa", BUILDER: "#f97316", VERIFIER: "#22d3ee", SHIPWRIGHT: "#a78bfa", AURA: "#c084fc", ATLAS: "#60a5fa", SAGE: "#22d3ee", FLOW: "#f472b6", ORBIT: "#34d399", SENTINEL: "#fb7185", MERCURY: "#818cf8" }; return colors[agent.toUpperCase()] ?? "#67e8f9"; }
function graphLevels(items: WorkItemV2[]) { const byId = new Map<string, WorkItemV2>(); items.forEach((item) => { byId.set(item.id, item); if (item.key) byId.set(item.key, item); }); const memo = new Map<string, number>(); const depth = (item: WorkItemV2, visiting = new Set<string>()): number => { if (memo.has(item.id)) return memo.get(item.id)!; if (visiting.has(item.id)) return 0; const next = new Set(visiting).add(item.id); const parents = (item.dependencies ?? []).map((id) => byId.get(id)).filter((parent): parent is WorkItemV2 => Boolean(parent)); const value = parents.length ? Math.max(...parents.map((parent) => depth(parent, next))) + 1 : 0; memo.set(item.id, value); return value; }; const levels: WorkItemV2[][] = []; items.forEach((item) => { const index = depth(item); (levels[index] ??= []).push(item); }); return levels; }
