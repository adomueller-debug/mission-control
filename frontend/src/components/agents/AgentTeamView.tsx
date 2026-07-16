import { ArrowDown, Braces, Brain, Database, Network, Wrench } from "lucide-react";

import {
  AGENT_STATUS_DOTS,
  AGENT_STATUS_LABELS,
  type AgentProfile,
} from "../../lib/agentTypes";
import { AgentGlyph } from "./AgentGlyph";

export function AgentTeamView({ agents }: { agents: AgentProfile[] }) {
  const byId = new Map(agents.map((agent) => [agent.id, agent]));
  const boss = byId.get("boss");
  const executives = ["forge", "aura", "sage"].map((id) => byId.get(id)).filter(Boolean) as AgentProfile[];
  const specialists = ["atlas", "flow", "orbit", "sentinel", "mercury"].map((id) => byId.get(id)).filter(Boolean) as AgentProfile[];
  const coding = agents.filter((agent) => agent.specialist);

  return (
    <section className="mt-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-cyan-300">Mission Control Core Team</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Agent Intelligence Network</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Ein hierarchisches Team mit klaren Zuständigkeiten, isoliertem Memory,
            eigenen Tool-Rechten und kontrollierten Delegationswegen.
          </p>
        </div>
        <div className="flex gap-2 text-xs text-slate-500">
          <Stat value={agents.length} label="Agenten" />
          <Stat value={agents.filter((agent) => agent.status === "active").length} label="Aktiv" />
          <Stat value={new Set(agents.flatMap((agent) => agent.tools)).size} label="Tools" />
        </div>
      </div>

      {boss && (
        <div className="mt-9 flex flex-col items-center">
          <AgentCard agent={boss} featured />
          <div className="h-8 w-px bg-gradient-to-b from-amber-300/40 to-white/10" />
          <div className="h-px w-[66%] bg-gradient-to-r from-transparent via-white/15 to-transparent" />
        </div>
      )}

      <div className="grid gap-4 pt-6 lg:grid-cols-3">
        {executives.map((agent) => <AgentCard key={agent.id} agent={agent} />)}
      </div>

      <div className="flex justify-center py-4 text-slate-700"><ArrowDown size={18} /></div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {specialists.map((agent) => <CompactAgentCard key={agent.id} agent={agent} parent={agent.parent_id ? byId.get(agent.parent_id)?.name : undefined} />)}
      </div>

      <section className="mt-8 overflow-hidden rounded-3xl border border-orange-300/10 bg-orange-300/[0.025]">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-orange-300/10 px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-orange-300/10 text-orange-200"><Braces size={18} /></div>
            <div><h2 className="text-sm font-semibold">FORGE Engineering Cell</h2><p className="mt-0.5 text-xs text-slate-600">Bestehende Coding-Agenten · neu verbunden</p></div>
          </div>
          <span className="rounded-full border border-orange-300/15 px-3 py-1 text-[10px] uppercase tracking-wider text-orange-200/70">4 specialists</span>
        </div>
        <div className="grid gap-px bg-white/[0.05] md:grid-cols-2 xl:grid-cols-4">
          {coding.map((agent) => (
            <div key={agent.id} className="bg-[#0b0f14] p-5">
              <div className="flex items-center gap-3"><AgentGlyph id={agent.id} color={agent.color} active={agent.status === "active"} /><div><p className="font-semibold">{agent.name}</p><p className="mt-1 text-xs text-slate-600">{agent.title}</p></div></div>
              <p className="mt-4 text-xs leading-5 text-slate-500">{agent.description}</p>
              {agent.legacy_ids.length > 0 && <p className="mt-3 text-[10px] text-orange-200/50">Verknüpft: {agent.legacy_ids.join(", ")}</p>}
            </div>
          ))}
        </div>
      </section>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <InfoCard icon={<Brain size={17} />} title="Isoliertes Memory" text="Jeder Agent schreibt Entscheidungen, Aufgaben und Ergebnisse in seinen eigenen persistenten Namespace." />
        <InfoCard icon={<Network size={17} />} title="Kontrollierte Handoffs" text="Delegationen folgen dem Organigramm und werden inklusive Kontext und Status am Run gespeichert." />
        <InfoCard icon={<Wrench size={17} />} title="Eigene Tool-Rechte" text="Agenten erhalten nur die Werkzeuge, die zu ihrer Rolle und Verantwortung gehören." />
      </div>
    </section>
  );
}

function AgentCard({ agent, featured = false }: { agent: AgentProfile; featured?: boolean }) {
  return (
    <article className={`mc-panel relative overflow-hidden rounded-2xl border bg-white/[0.025] p-5 ${featured ? "w-full max-w-xl border-amber-300/20 shadow-2xl shadow-amber-500/5" : "border-white/[0.07]"}`}>
      <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent" />
      <div className="flex items-start gap-4">
        <AgentGlyph id={agent.id} color={agent.color} size={featured ? "lg" : "md"} active={agent.status === "active"} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2"><h2 className={`${featured ? "text-xl" : "text-lg"} font-semibold tracking-wide`}>{agent.name}</h2><StatusDot status={agent.status} /></div>
          <p className="mt-1 text-xs text-slate-500">{agent.title}</p>
          <p className="mt-3 text-sm leading-6 text-slate-400">{agent.description}</p>
        </div>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-2 text-[10px]">
        <Meta icon={<Database size={12} />} label="Memory" value={agent.memory_namespace} />
        <Meta icon={<Brain size={12} />} label="Model" value={agent.preferred_model} />
      </div>
      <div className="mt-4 flex flex-wrap gap-1.5">{agent.capabilities.slice(0, 5).map((item) => <Tag key={item}>{item}</Tag>)}</div>
    </article>
  );
}

function CompactAgentCard({ agent, parent }: { agent: AgentProfile; parent?: string }) {
  return (
    <article className="mc-panel rounded-2xl border border-white/[0.07] bg-white/[0.02] p-4 hover:-translate-y-0.5 hover:border-white/[0.12]">
      <div className="flex items-center justify-between"><AgentGlyph id={agent.id} color={agent.color} active={agent.status === "active"} /><StatusDot status={agent.status} /></div>
      <h3 className="mt-4 font-semibold tracking-wide">{agent.name}</h3>
      <p className="mt-1 text-[11px] text-slate-600">{agent.title}</p>
      <p className="mt-3 line-clamp-3 text-xs leading-5 text-slate-500">{agent.description}</p>
      <p className="mt-4 text-[10px] uppercase tracking-wider text-slate-700">Reports to {parent ?? "BOSS"}</p>
    </article>
  );
}

function StatusDot({ status }: { status: AgentProfile["status"] }) {
  return <span title={AGENT_STATUS_LABELS[status]} className={`h-1.5 w-1.5 rounded-full ${AGENT_STATUS_DOTS[status]}`} />;
}

function Meta({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="min-w-0 rounded-lg bg-black/20 p-2 text-slate-600"><span className="flex items-center gap-1">{icon}{label}</span><span className="mt-1 block truncate text-slate-400">{value}</span></div>;
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-md border border-white/[0.06] bg-white/[0.025] px-2 py-1 text-[10px] text-slate-500">{children}</span>;
}

function Stat({ value, label }: { value: number; label: string }) {
  return <div className="rounded-xl border border-white/[0.07] bg-white/[0.025] px-4 py-2 text-center"><p className="font-semibold text-slate-300">{value}</p><p className="text-[10px] text-slate-600">{label}</p></div>;
}

function InfoCard({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4"><div className="flex items-center gap-2 text-sm text-slate-300">{icon}{title}</div><p className="mt-2 text-xs leading-5 text-slate-600">{text}</p></div>;
}
