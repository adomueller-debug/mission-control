import { Check, ChevronLeft, ChevronRight, GitCompare, X } from "lucide-react";

import { usePatchStore } from "../../lib/patchStore";

export default function PatchPanel() {
  const {
    patches,
    activeIndex,
    error,
    applyActivePatch,
    rejectActivePatch,
    selectPatch,
  } = usePatchStore();

  const patch = patches[activeIndex];

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-2">
          <GitCompare size={18} className="shrink-0 text-cyan-400" />

          <div className="min-w-0">
            <h2 className="text-lg font-semibold">Patch Review</h2>
            <p className="truncate text-sm text-slate-500">
              {patch?.path ?? "Noch kein Patch vorhanden"}
            </p>
          </div>
        </div>

        {patch && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={activeIndex === 0}
              onClick={() => selectPatch(activeIndex - 1)}
              className="rounded-lg border border-slate-700 p-2 disabled:opacity-30"
            >
              <ChevronLeft size={17} />
            </button>

            <span className="text-sm text-slate-400">
              {activeIndex + 1} / {patches.length}
            </span>

            <button
              type="button"
              disabled={activeIndex >= patches.length - 1}
              onClick={() => selectPatch(activeIndex + 1)}
              className="rounded-lg border border-slate-700 p-2 disabled:opacity-30"
            >
              <ChevronRight size={17} />
            </button>

            <button
              type="button"
              onClick={() => void applyActivePatch()}
              className="flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950"
            >
              <Check size={16} />
              Accept
            </button>

            <button
              type="button"
              onClick={() => void rejectActivePatch()}
              className="flex items-center gap-2 rounded-lg bg-rose-500 px-3 py-2 text-sm font-semibold text-white"
            >
              <X size={16} />
              Reject
            </button>
          </div>
        )}
      </div>

      <pre className="mt-5 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-sm leading-6 text-slate-300">
        {patch?.diff || "# Noch kein Patch vorhanden"}
      </pre>

      {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
    </section>
  );
}
