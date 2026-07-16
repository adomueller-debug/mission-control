import {
  Atom,
  Bot,
  BrainCircuit,
  Crown,
  Database,
  GitBranch,
  Hammer,
  Network,
  Orbit,
  Palette,
  Radar,
  Rocket,
  Search,
  ShieldCheck,
  Workflow,
} from "lucide-react";

const icons: Record<string, React.ComponentType<{ size?: number; strokeWidth?: number }>> = {
  boss: Crown,
  forge: Hammer,
  aura: Palette,
  sage: BrainCircuit,
  atlas: Search,
  flow: Workflow,
  orbit: Database,
  sentinel: ShieldCheck,
  mercury: Rocket,
  forge_planner: Network,
  forge_builder: GitBranch,
  forge_reviewer: Radar,
  forge_publisher: Orbit,
};

const palettes: Record<string, { glow: string; line: string; core: string }> = {
  gold: { glow: "shadow-amber-400/20", line: "border-amber-300/35", core: "bg-amber-300/10 text-amber-200" },
  orange: { glow: "shadow-orange-400/20", line: "border-orange-300/30", core: "bg-orange-400/10 text-orange-200" },
  violet: { glow: "shadow-violet-400/20", line: "border-violet-300/30", core: "bg-violet-400/10 text-violet-200" },
  cyan: { glow: "shadow-cyan-400/20", line: "border-cyan-300/30", core: "bg-cyan-400/10 text-cyan-200" },
  blue: { glow: "shadow-blue-400/20", line: "border-blue-300/30", core: "bg-blue-400/10 text-blue-200" },
  pink: { glow: "shadow-pink-400/20", line: "border-pink-300/30", core: "bg-pink-400/10 text-pink-200" },
  emerald: { glow: "shadow-emerald-400/20", line: "border-emerald-300/30", core: "bg-emerald-400/10 text-emerald-200" },
  red: { glow: "shadow-red-400/20", line: "border-red-300/30", core: "bg-red-400/10 text-red-200" },
  indigo: { glow: "shadow-indigo-400/20", line: "border-indigo-300/30", core: "bg-indigo-400/10 text-indigo-200" },
};

export function AgentGlyph({ id, color, size = "md", active = false }: { id: string; color: string; size?: "sm" | "md" | "lg"; active?: boolean }) {
  const Icon = icons[id] ?? (id.startsWith("forge_") ? Atom : Bot);
  const palette = palettes[color] ?? palettes.cyan;
  const dimensions = size === "lg" ? "h-20 w-20" : size === "sm" ? "h-9 w-9" : "h-14 w-14";
  const iconSize = size === "lg" ? 29 : size === "sm" ? 15 : 21;

  return (
    <div className={`agent-glyph relative grid shrink-0 place-items-center rounded-full shadow-xl ${dimensions} ${palette.glow} ${active ? "is-active" : ""}`}>
      <span className={`agent-orbit absolute inset-0 rounded-full border ${palette.line}`} />
      <span className={`agent-orbit-reverse absolute inset-[5px] rounded-full border border-dashed ${palette.line}`} />
      <span className={`relative grid h-[68%] w-[68%] place-items-center rounded-full border ${palette.line} ${palette.core}`}>
        <Icon size={iconSize} strokeWidth={1.65} />
        <span className="agent-scan absolute inset-x-1 top-1/2 h-px bg-current opacity-30" />
      </span>
      <span className={`absolute right-[4%] top-[12%] h-1.5 w-1.5 rounded-full ${active ? "animate-pulse bg-white" : "bg-white/35"}`} />
    </div>
  );
}
