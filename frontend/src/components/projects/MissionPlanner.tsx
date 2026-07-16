import { useState } from "react";
import { ArrowRight, Bot, Check, ChevronDown, Crown, RefreshCw, Sparkles, TriangleAlert } from "lucide-react";

import type { AgentProfile } from "../../lib/agentTypes";
import { api } from "../../lib/api";
import type { MissionPlan } from "../../lib/missionTypes";
import type { Project } from "../../lib/projectTypes";

export function MissionPlanner({ project, agents, onApproved }: { project: Project; agents: AgentProfile[]; onApproved: () => Promise<void> }) {
  const [goal, setGoal] = useState(project.goal || project.name);
  const [plan, setPlan] = useState<MissionPlan | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const result = await api<MissionPlan>(`/api/v1/projects/${project.id}/mission-plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal }),
      });
      setPlan(result);
      setOpen(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "BOSS konnte keinen Plan erstellen");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!plan) return;
    setBusy(true);
    try {
      const result = await api<{ plan: MissionPlan }>(`/api/v1/mission-plans/${plan.id}/approve`, { method: "POST" });
      setPlan(result.plan);
      await onApproved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Plan konnte nicht übernommen werden");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-5 rounded-2xl border border-amber-300/10 bg-[linear-gradient(135deg,rgba(251,191,36,0.045),rgba(34,211,238,0.025))] p-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-amber-300/10 text-amber-300"><Crown size={17} /></div>
        <div className="min-w-0 flex-1"><h3 className="text-sm font-semibold">Mit BOSS planen</h3><p className="mt-0.5 text-[11px] text-slate-600">Ziel in Agentenaufgaben, Abhängigkeiten und Integrationen zerlegen.</p></div>
        <button onClick={() => setOpen((value) => !value)} className="grid h-8 w-8 place-items-center rounded-lg text-slate-600 hover:bg-white/[0.04]"><ChevronDown size={15} className={`transition ${open ? "rotate-180" : ""}`} /></button>
      </div>
      {open && (
        <div className="mt-4 border-t border-white/[0.06] pt-4">
          <div className="flex gap-2"><textarea value={goal} onChange={(event) => setGoal(event.target.value)} className="min-h-16 flex-1 resize-none rounded-xl border border-white/[0.07] bg-[#080b10] px-3 py-2.5 text-xs leading-5 outline-none focus:border-amber-300/30" placeholder="Welches Ergebnis soll das Team erreichen?" /><button disabled={busy || goal.trim().length < 3} onClick={() => void generate()} className="flex shrink-0 items-center gap-2 self-end rounded-xl bg-amber-200 px-3 py-2.5 text-xs font-semibold text-slate-950 disabled:opacity-30">{busy ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}Planen</button></div>
          {error && <p className="mt-2 flex items-center gap-1.5 text-[10px] text-rose-300"><TriangleAlert size={11} />{error}</p>}
          {plan && (
            <div className="mt-4">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-medium text-slate-200">{plan.summary}</p><p className="mt-1 max-w-3xl text-[11px] leading-5 text-slate-500">{plan.strategy}</p></div><span className={`rounded px-2 py-1 text-[9px] uppercase ${plan.planner_mode === "ollama" ? "bg-cyan-300/10 text-cyan-300" : "bg-violet-300/10 text-violet-300"}`}>{plan.planner_mode === "ollama" ? "Ollama Plan" : "Sicherer Fallback"}</span></div>
              <div className="mt-4 space-y-2">{plan.tasks.map((task) => { const agent = agents.find((item) => item.id === task.agent_id); return <div key={task.id} className="rounded-xl border border-white/[0.06] bg-black/15 p-3"><div className="flex items-start gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-white/[0.05] text-[10px] text-slate-500">{task.sequence}</span><div className="min-w-0 flex-1"><p className="text-xs font-medium text-slate-300">{task.title}</p><p className="mt-1 line-clamp-2 text-[10px] leading-4 text-slate-600">{task.description}</p><div className="mt-2 flex flex-wrap items-center gap-1 text-[9px] text-slate-600"><span className="flex items-center gap-1 rounded bg-white/[0.04] px-1.5 py-1"><Bot size={9} />{agent?.name ?? task.agent_id}</span>{task.delegation_path.map((node, index) => <span key={`${node}-${index}`} className="flex items-center gap-1">{index > 0 && <ArrowRight size={8} />}{node.toUpperCase()}</span>)}{task.integration_ids.map((id) => <span key={id} className="rounded bg-cyan-300/[0.06] px-1.5 py-1 text-cyan-500">{id}</span>)}</div></div></div></div>; })}</div>
              {plan.status === "draft" ? <div className="mt-4 flex items-center justify-between rounded-xl border border-white/[0.06] bg-black/10 p-3"><p className="max-w-xl text-[10px] leading-4 text-slate-600">Übernehmen legt die Aufgaben im Projektboard an und markiert benötigte Integrationen. Externe Aktionen starten dadurch noch nicht.</p><button disabled={busy} onClick={() => void approve()} className="flex shrink-0 items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300"><Check size={13} />Plan übernehmen</button></div> : <p className="mt-4 flex items-center gap-1.5 text-xs text-emerald-300"><Check size={13} />Plan wurde in das Projektboard übernommen.</p>}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
