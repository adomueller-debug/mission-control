import { useEffect, useState } from "react";
import { ChevronRight, FileCode2, FolderOpen } from "lucide-react";
import { useFileStore } from "../../lib/fileStore";

export default function FileTree() {
  const [files, setFiles] = useState<string[]>([]);
  const { selectedFile, openFile } = useFileStore();

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/files/");

        if (!response.ok) return;

        setFiles(await response.json());
      } catch {
        setFiles([]);
      }
    };

    void load();
  }, []);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-4 flex items-center gap-2">
        <FolderOpen size={18} className="text-cyan-400" />
        <h2 className="text-lg font-semibold">Projekt</h2>
      </div>

      <div className="max-h-[500px] overflow-auto space-y-1">
        {files.map((file) => (
          <button
            key={file}
            onClick={() => void openFile(file)}
            className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition ${
              selectedFile === file
                ? "bg-cyan-900/40 text-cyan-300"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            <ChevronRight size={14} />
            <FileCode2 size={15} />
            <span className="truncate">{file}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
