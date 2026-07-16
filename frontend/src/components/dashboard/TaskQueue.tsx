import { useEffect, useState } from "react";
import { CheckCircle2, Clock3, Loader2, XCircle } from "lucide-react";

type Task = {
  id: string;
  instruction: string;
  status: string;
  agent_id: string;
};

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") {
    return <CheckCircle2 size={17} className="text-emerald-400" />;
  }

  if (status === "failed") {
    return <XCircle size={17} className="text-rose-400" />;
  }

  if (status === "running") {
    return <Loader2 size={17} className="animate-spin text-cyan-400" />;
  }

  return <Clock3 size={17} className="text-amber-400" />;
}

export default function TaskQueue() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const load = async () => {
      const response = await fetch("http://127.0.0.1:8000/tasks/");

      if (!response.ok) return;

      const result = (await response.json()) as Task[];

      setTasks(
        result
          .filter((task) => task.agent_id === "mission-control")
          .slice(-8)
          .reverse(),
      );
    };

    void load();

    const timer = window.setInterval(() => void load(), 2000);

    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="text-lg font-semibold">Task Queue</h2>

      <div className="mt-4 space-y-3">
        {tasks.length === 0 ? (
          <p className="text-sm text-slate-500">Noch keine Tasks vorhanden.</p>
        ) : (
          tasks.map((task) => (
            <article
              key={task.id}
              className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4"
            >
              <StatusIcon status={task.status} />

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">
                  {task.instruction}
                </p>

                <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                  {task.status}
                </p>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
