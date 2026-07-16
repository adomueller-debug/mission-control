import { useState } from "react";
import { ClipboardList, Code2, Copy, Search } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

type ResultTabsProps = {
  plan: string;
  implementation: string;
  analysis: string;
};

const tabs = [
  { key: "plan", label: "Plan", icon: ClipboardList, language: "markdown" },
  { key: "implementation", label: "Umsetzung", icon: Code2, language: "python" },
  { key: "analysis", label: "Analyse", icon: Search, language: "markdown" },
] as const;

export default function ResultTabs({
  plan,
  implementation,
  analysis,
}: ResultTabsProps) {
  const [active, setActive] =
    useState<(typeof tabs)[number]["key"]>("plan");

  const content = {
    plan,
    implementation,
    analysis,
  };

  const activeTab =
    tabs.find((tab) => tab.key === active) ?? tabs[0];

  async function copy() {
    await navigator.clipboard.writeText(content[active]);
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
      <div className="flex items-center justify-between border-b border-slate-800">
        <div className="flex">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => setActive(key)}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium ${
                active === key
                  ? "border-cyan-400 text-cyan-300"
                  : "border-transparent text-slate-500 hover:text-slate-300"
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        <button
          onClick={copy}
          className="mr-3 flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
        >
          <Copy size={15} />
          Copy
        </button>
      </div>

      <SyntaxHighlighter
        language={activeTab.language}
        style={oneDark}
        showLineNumbers
        wrapLongLines
        customStyle={{
          margin: 0,
          background: "transparent",
          fontSize: "0.9rem",
          minHeight: "520px",
        }}
      >
        {content[active]}
      </SyntaxHighlighter>
    </div>
  );
}
