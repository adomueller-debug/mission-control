import { useEffect, useState } from "react";
import { Braces } from "lucide-react";

import ResultTabs from "./ResultTabs";

type Task = {
  id: string;
  instruction: string;
  agent_id: string;
  status: string;
  result?: string | null;
};

type AgentResult = {
  plan?: unknown;
  implementation?: unknown;
  analysis?: unknown;
};

function format(value: unknown) {
  if (value === undefined || value === null || value === "") {
    return "Noch kein Ergebnis vorhanden.";
  }

  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

function parseResult(result?: string | null): AgentResult {
  if (!result) return {};

  try {
    return JSON.parse(result) as AgentResult;
  } catch {
    return {
      implementation: result,
    };
  }
}

export default function TaskResult() {
  const [task, setTask] = useState<Task | null>(null);

  useEffect(() => {
    const load = async () => {
      const response = await fetch("http://127.0.0.1:8000/tasks/");

      if (!response.ok) return;

      const tasks = (await response.json()) as Task[];

      const latest =
        tasks
          .filter((item) => item.agent_id === "mission-control")
          .at(-1) ?? null;

      setTask(latest);
    };

    void load();

    const timer = window.setInterval(() => void load(), 2000);

    return () => window.clearInterval(timer);
  }, []);

  if (!task) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-lg font-semibold">Letztes Ergebnis</h2>
        <p className="mt-4 text-sm text-slate-500">
          Noch kein Auftrag vorhanden.
        </p>
      </section>
    );
  }

  const result = parseResult(task.result);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Braces size={19} className="text-cyan-400" />
            <h2 className="text-lg font-semibold">Letztes Ergebnis</h2>
          </div>

          <p className="mt-2 text-sm text-slate-400">{task.instruction}</p>
        </div>

        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            task.status === "completed"
              ? "bg-emerald-950 text-emerald-300"
              : task.status === "failed"
                ? "bg-rose-950 text-rose-300"
                : "bg-amber-950 text-amber-300"
          }`}
        >
          {task.status}
        </span>
      </div>

      <div className="mt-6">
        <ResultTabs
          plan={format(result.plan)}
          implementation={format(result.implementation)}
          analysis={format(result.analysis)}
        />
      </div>
    </section>
  );
}
