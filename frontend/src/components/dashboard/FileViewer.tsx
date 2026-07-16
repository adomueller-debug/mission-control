import { useEffect, useState } from "react";
import { FileCode2, GitCompare } from "lucide-react";

import { useFileStore } from "../../lib/fileStore";
import { usePatchStore } from "../../lib/patchStore";

export default function FileViewer() {
  const { selectedFile, content } = useFileStore();
  const { createPatch, loading, error } = usePatchStore();

  const [draft, setDraft] = useState(content);
  const [message, setMessage] = useState("");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDraft(content);
    setMessage("");
  }, [content]);

  async function generatePatch() {
    if (!selectedFile || draft === content) return;

    setMessage("");
    await createPatch(selectedFile, draft);

    if (!usePatchStore.getState().error) {
      setMessage("Patch wurde erstellt. Bitte unten prüfen.");
    }
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-2">
          <FileCode2 size={18} className="shrink-0 text-cyan-400" />

          <h2 className="truncate text-lg font-semibold">
            {selectedFile ?? "Keine Datei geöffnet"}
          </h2>
        </div>

        <button
          type="button"
          onClick={() => void generatePatch()}
          disabled={!selectedFile || loading || draft === content}
          className="flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <GitCompare size={16} />
          {loading ? "Erstellt..." : "Patch erstellen"}
        </button>
      </div>

      <textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        disabled={!selectedFile}
        spellCheck={false}
        className="min-h-[620px] w-full resize-y rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-sm leading-6 text-slate-200 outline-none focus:border-cyan-500 disabled:cursor-not-allowed disabled:text-slate-600"
        placeholder="// Datei auswählen..."
      />

      {(message || error) && (
        <p className={`mt-3 text-sm ${error ? "text-rose-400" : "text-slate-400"}`}>
          {error ?? message}
        </p>
      )}
    </section>
  );
}
