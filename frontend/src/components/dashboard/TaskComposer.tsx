import { useState } from "react";
import { Send } from "lucide-react";

import { startTask } from "../../lib/taskWorkflow";

export default function TaskComposer() {
  const [task, setTask] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (!task.trim()) return;

    setLoading(true);

    try {
      await startTask(task);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="mb-4 text-lg font-semibold">Neue Aufgabe</h2>

      <textarea
        value={task}
        onChange={(e) => setTask(e.target.value)}
        placeholder="Beschreibe deine Aufgabe..."
        className="min-h-[120px] w-full rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm outline-none focus:border-cyan-500"
      />

      <button
        onClick={() => void submit()}
        disabled={loading}
        className="mt-4 flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50"
      >
        <Send size={16} />
        {loading ? "Plane..." : "Planner starten"}
      </button>
    </section>
  );
}
