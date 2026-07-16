import { ClipboardList } from "lucide-react";
import { usePlannerStore } from "../../lib/plannerStore";

export default function ExecutionPlan() {
  const { goal, summary, steps } = usePlannerStore();

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-4 flex items-center gap-2">
        <ClipboardList size={18} className="text-cyan-400" />
        <h2 className="text-lg font-semibold">Execution Plan</h2>
      </div>

      {goal ? (
        <>
          <p className="font-semibold">{goal}</p>
          <p className="mt-1 text-sm text-slate-400">{summary}</p>

          <div className="mt-5 space-y-3">
            {steps.map((step) => (
              <div
                key={step.id}
                className="rounded-lg border border-slate-800 bg-slate-950 p-3"
              >
                <div className="flex justify-between">
                  <strong>{step.title}</strong>
                  <span className="text-cyan-400">{step.agent}</span>
                </div>

                <p className="mt-1 text-sm text-slate-400">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="text-sm text-slate-500">
          Noch kein Plan erstellt.
        </p>
      )}
    </section>
  );
}
