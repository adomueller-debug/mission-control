from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import escape
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.workspace_security import resolve_workspace_path
from backend.app.models.execution_plan import ExecutionPlan
from backend.app.services.validator import resolve_executable, run_command


class BlueprintFile(BaseModel):
    path: str
    purpose: str
    required: bool = True


class BlueprintArtifact(BaseModel):
    version: str = "1.0"
    artifact_type: str = "technical_blueprint"
    approved: bool = True
    repository_type: str
    manifests: list[str] = Field(default_factory=list)
    architecture: list[str]
    file_plan: list[BlueprintFile]
    test_plan: list[str]
    risks: list[str]
    quality_gates: list[str]


def _product_name(task: str, plan: ExecutionPlan) -> str:
    """Extract a useful, deterministic product name without another model call."""
    candidates = (
        r"(?:Kernaussagen:\s*)?([A-ZÄÖÜ][^:\n]{2,70}):\s*(?:Opportunity|Chance|Ziel)",
        r"Projekt:\s*([^\n]{3,70})",
        r"(?:für|fuer)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 &'.-]{2,60})",
    )
    for pattern in candidates:
        match = re.search(pattern, task)
        if match:
            return " ".join(match.group(1).strip().split())
    return " ".join((plan.summary or "Digitales Erlebnis").strip().split())


def create_react_vite_scaffold(
    plan: ExecutionPlan,
    task: str,
) -> list[dict[str, str]]:
    """Return the immutable, professional baseline for a generated website.

    The local model should customize the product, not reinvent its build system,
    accessibility baseline or responsive and motion foundations on every run.
    """
    if not plan.creation_mode or not plan.output_directory:
        return []

    base = plan.output_directory.rstrip("/")
    product_name = _product_name(task, plan)
    js_name = json.dumps(product_name, ensure_ascii=False)
    html_name = escape(product_name)
    package = {
        "name": re.sub(r"[^a-z0-9]+", "-", product_name.lower()).strip("-")
        or "mission-control-product",
        "private": True,
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite --host 127.0.0.1",
            "build": "tsc -b && vite build",
            "preview": "vite preview --host 127.0.0.1",
        },
        "dependencies": {"react": "^19.2.7", "react-dom": "^19.2.7"},
        "devDependencies": {
            "@types/react": "^19.2.17",
            "@types/react-dom": "^19.2.3",
            "@vitejs/plugin-react": "^6.0.3",
            "typescript": "~6.0.2",
            "vite": "^8.1.1",
        },
    }
    app = f'''import {{ useEffect }} from "react";
import "./styles.css";

const productName = {js_name};

const services = [
  {{ number: "01", title: "Klarer Auftritt", text: "Eine fokussierte Nutzerführung bringt Angebot, Qualität und nächsten Schritt auf den Punkt." }},
  {{ number: "02", title: "Starke Präsenz", text: "Ein eigenständiges visuelles System schafft Wiedererkennung auf jedem Bildschirm." }},
  {{ number: "03", title: "Direkter Kontakt", text: "Gut platzierte Kontaktpunkte machen aus Interesse eine konkrete Anfrage." }},
];

export default function App() {{
  useEffect(() => {{
    const elements = document.querySelectorAll<HTMLElement>("[data-reveal]");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {{
      elements.forEach((element) => element.classList.add("is-visible"));
      return;
    }}
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("is-visible")),
      {{ threshold: 0.16, rootMargin: "0px 0px -8%" }},
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }}, []);

  return (
    <div className="site-shell">
      <a className="skip-link" href="#inhalt">Zum Inhalt springen</a>
      <header className="site-header">
        <a className="wordmark" href="#start" aria-label={{`${{productName}} – Startseite`}}>{{productName}}</a>
        <nav aria-label="Hauptnavigation">
          <a href="#leistungen">Leistungen</a>
          <a href="#profil">Profil</a>
          <a className="nav-cta" href="#kontakt">Kontakt</a>
        </nav>
      </header>

      <main id="inhalt">
        <section className="hero" id="start" aria-labelledby="hero-title">
          <div className="hero-glow" aria-hidden="true" />
          <p className="eyebrow" data-reveal>Digitaler Auftritt · Konzeptvorschau</p>
          <h1 id="hero-title" data-reveal>
            Persönlich im Kern.<br /><span>Unverwechselbar im Web.</span>
          </h1>
          <p className="hero-copy" data-reveal>
            Ein moderner digitaler Auftritt für {{productName}}, entwickelt für einen starken ersten Eindruck und einen einfachen Weg zur Anfrage.
          </p>
          <div className="hero-actions" data-reveal>
            <a className="button button-primary" href="#kontakt">Angebot anfragen <span aria-hidden="true">↗</span></a>
            <a className="text-link" href="#leistungen">Konzept entdecken <span aria-hidden="true">↓</span></a>
          </div>
          <div className="scroll-cue" aria-hidden="true"><span /> Scroll</div>
        </section>

        <section className="statement" id="profil" data-reveal>
          <p className="section-label">Der Anspruch</p>
          <h2>Weniger Ablenkung.<br />Mehr Wirkung.</h2>
          <p>Klare Inhalte, großzügige Flächen und gezielte Bewegung führen Besucher intuitiv durch das Angebot. Konkrete Unternehmensangaben werden vor Veröffentlichung gemeinsam abgestimmt.</p>
        </section>

        <section className="services" id="leistungen" aria-labelledby="services-title">
          <div className="section-heading" data-reveal>
            <p className="section-label">Das digitale Erlebnis</p>
            <h2 id="services-title">Gebaut für Aufmerksamkeit und Vertrauen.</h2>
          </div>
          <div className="service-grid">
            {{services.map((service) => (
              <article className="service-card" data-reveal key={{service.number}}>
                <span>{{service.number}}</span><h3>{{service.title}}</h3><p>{{service.text}}</p>
              </article>
            ))}}
          </div>
        </section>

        <section className="contact" id="kontakt" data-reveal>
          <p className="section-label">Nächster Schritt</p>
          <h2>Aus einem guten ersten Eindruck wird ein Gespräch.</h2>
          <p>Diese Konzeptvorschau zeigt die gestalterische Richtung. Inhalte, Leistungen und Kontaktdaten werden vor dem Livegang verifiziert.</p>
          <a className="button button-light" href="mailto:kontakt@example.com">Gespräch vorbereiten <span aria-hidden="true">↗</span></a>
        </section>
      </main>

      <footer><strong>{{productName}}</strong><span>Digitale Konzeptvorschau</span><a href="#start">Nach oben ↑</a></footer>
    </div>
  );
}}
'''
    css = '''@import url("https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Manrope:wght@500;600;700&display=swap");

:root {
  color-scheme: dark;
  --ink: #f5f7f2;
  --muted: #a5aca3;
  --surface: #0b0e0d;
  --surface-raised: #121716;
  --line: rgba(255, 255, 255, 0.12);
  --accent: #c9ff4f;
  --accent-dark: #162106;
  --content: min(1180px, calc(100vw - 48px));
  --radius: 24px;
  --ease: cubic-bezier(.22, 1, .36, 1);
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; background: var(--surface); }
body { margin: 0; min-width: 320px; color: var(--ink); background: var(--surface); font-family: "DM Sans", system-ui, sans-serif; line-height: 1.6; }
a { color: inherit; text-decoration: none; }
.site-shell { overflow: clip; }
.skip-link { position: fixed; z-index: 100; top: 12px; left: 12px; padding: 10px 16px; color: #071000; background: var(--accent); border-radius: 999px; transform: translateY(-160%); }
.skip-link:focus { transform: translateY(0); }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }

.site-header { position: absolute; z-index: 20; top: 0; left: 50%; width: var(--content); height: 92px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--line); transform: translateX(-50%); }
.wordmark { max-width: 46vw; overflow: hidden; font-family: "Manrope", sans-serif; font-weight: 700; font-size: 1.05rem; text-overflow: ellipsis; white-space: nowrap; }
nav { display: flex; align-items: center; gap: clamp(18px, 3vw, 42px); font-size: .9rem; }
nav a { color: var(--muted); transition: color .25s ease; }
nav a:hover { color: var(--ink); }
.nav-cta { padding: 9px 16px; border: 1px solid var(--line); border-radius: 999px; }

.hero { position: relative; min-height: 100svh; padding: clamp(160px, 22vh, 230px) max(24px, calc((100vw - 1180px) / 2)) 80px; display: flex; flex-direction: column; justify-content: center; isolation: isolate; }
.hero-glow { position: absolute; z-index: -1; top: -25%; right: -15%; width: min(70vw, 900px); aspect-ratio: 1; border-radius: 50%; background: radial-gradient(circle, rgba(201,255,79,.16), transparent 64%); filter: blur(12px); animation: breathe 8s ease-in-out infinite alternate; }
.eyebrow, .section-label { margin: 0 0 24px; color: var(--accent); font-size: .72rem; font-weight: 600; letter-spacing: .18em; text-transform: uppercase; }
h1, h2, h3 { margin: 0; font-family: "Manrope", sans-serif; line-height: .98; letter-spacing: -.045em; }
h1 { max-width: 1050px; font-size: clamp(3.35rem, 8.5vw, 8.2rem); }
h1 span { color: var(--muted); }
.hero-copy { max-width: 640px; margin: 38px 0 0 auto; color: #cbd0ca; font-size: clamp(1.08rem, 1.7vw, 1.35rem); }
.hero-actions { max-width: 640px; width: 100%; margin: 36px 0 0 auto; display: flex; align-items: center; gap: 28px; }
.button { display: inline-flex; align-items: center; justify-content: center; gap: 18px; min-height: 54px; padding: 0 25px; border-radius: 999px; font-weight: 600; transition: transform .3s var(--ease), background-color .3s ease; }
.button:hover { transform: translateY(-3px); }
.button-primary { color: #101507; background: var(--accent); box-shadow: 0 18px 50px rgba(201,255,79,.12); }
.text-link { color: var(--muted); border-bottom: 1px solid var(--line); }
.scroll-cue { position: absolute; left: max(24px, calc((100vw - 1180px) / 2)); bottom: 30px; display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; }
.scroll-cue span { width: 34px; height: 1px; background: var(--accent); animation: pulse-line 2s ease-in-out infinite; }

.statement, .services, .contact { width: var(--content); margin-inline: auto; padding-block: clamp(110px, 15vw, 200px); }
.statement { display: grid; grid-template-columns: .7fr 1.6fr 1fr; gap: clamp(28px, 5vw, 84px); align-items: start; border-top: 1px solid var(--line); }
.statement h2, .section-heading h2, .contact h2 { font-size: clamp(2.7rem, 5.5vw, 5.4rem); }
.statement > p:last-child { margin: 8px 0 0; color: var(--muted); }
.services { border-top: 1px solid var(--line); }
.section-heading { max-width: 870px; }
.service-grid { margin-top: clamp(60px, 9vw, 110px); display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--line); border: 1px solid var(--line); }
.service-card { min-height: 360px; padding: clamp(28px, 4vw, 50px); display: flex; flex-direction: column; background: var(--surface); transition: background-color .35s ease, transform .35s var(--ease); }
.service-card:hover { z-index: 1; background: var(--surface-raised); transform: translateY(-6px); }
.service-card > span { color: var(--accent); font-size: .78rem; }
.service-card h3 { margin-top: auto; font-size: clamp(1.7rem, 3vw, 2.6rem); }
.service-card p { color: var(--muted); margin: 22px 0 0; }
.contact { width: 100%; padding-inline: max(24px, calc((100vw - 1180px) / 2)); background: var(--accent); color: #101508; }
.contact .section-label { color: #405016; }
.contact h2 { max-width: 930px; }
.contact > p:not(.section-label) { max-width: 620px; margin: 30px 0; color: #35400e; }
.button-light { background: #101508; color: var(--ink); }
footer { width: var(--content); min-height: 150px; margin-inline: auto; display: flex; align-items: center; justify-content: space-between; gap: 24px; color: var(--muted); font-size: .82rem; }
footer strong { color: var(--ink); font-family: "Manrope", sans-serif; }

[data-reveal] { opacity: 0; transform: translateY(42px); transition: opacity .9s var(--ease), transform .9s var(--ease); }
[data-reveal].is-visible { opacity: 1; transform: translateY(0); }
.service-card:nth-child(2) { transition-delay: .1s; }
.service-card:nth-child(3) { transition-delay: .2s; }
@keyframes breathe { to { transform: translate(-5%, 7%) scale(1.08); opacity: .7; } }
@keyframes pulse-line { 50% { transform: scaleX(.45); transform-origin: left; opacity: .45; } }

@media (max-width: 800px) {
  :root { --content: min(100% - 32px, 1180px); }
  .site-header { height: 76px; }
  nav a:not(.nav-cta) { display: none; }
  .hero { padding-inline: 16px; }
  .hero-copy, .hero-actions { margin-left: 0; }
  .statement { grid-template-columns: 1fr; }
  .service-grid { grid-template-columns: 1fr; }
  .service-card { min-height: 280px; }
  footer { padding-block: 36px; flex-direction: column; align-items: flex-start; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
  [data-reveal] { opacity: 1; transform: none; }
}
'''
    files = {
        "package.json": json.dumps(package, indent=2, ensure_ascii=False) + "\n",
        "index.html": f'''<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="Digitale Konzeptvorschau für {html_name}." />
    <title>{html_name} · Digitales Erlebnis</title>
  </head>
  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
''',
        "tsconfig.json": '''{"files":[],"references":[{"path":"./tsconfig.app.json"},{"path":"./tsconfig.node.json"}]}\n''',
        "tsconfig.app.json": '''{"compilerOptions":{"target":"ES2022","useDefineForClassFields":true,"lib":["ES2022","DOM","DOM.Iterable"],"allowJs":false,"skipLibCheck":true,"esModuleInterop":true,"allowSyntheticDefaultImports":true,"strict":true,"forceConsistentCasingInFileNames":true,"module":"ESNext","moduleResolution":"Bundler","resolveJsonModule":true,"isolatedModules":true,"noEmit":true,"jsx":"react-jsx"},"include":["src"]}\n''',
        "tsconfig.node.json": '''{"compilerOptions":{"composite":true,"skipLibCheck":true,"module":"ESNext","moduleResolution":"Bundler","allowImportingTsExtensions":true,"noEmit":true},"include":["vite.config.ts"]}\n''',
        "vite.config.ts": '''import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\n\nexport default defineConfig({ plugins: [react()] });\n''',
        "src/vite-env.d.ts": '''/// <reference types="vite/client" />\n''',
        "src/main.tsx": '''import { StrictMode } from "react";\nimport { createRoot } from "react-dom/client";\nimport App from "./App";\n\ncreateRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);\n''',
        "src/App.tsx": app,
        "src/styles.css": css,
    }
    return [
        {"path": f"{base}/{path}", "content": content}
        for path, content in files.items()
    ]


def create_technical_blueprint(
    plan: ExecutionPlan,
    workspace: str,
) -> BlueprintArtifact:
    """Create a deterministic, auditable technical analysis before coding."""
    root = Path(workspace).resolve()
    manifests = [
        name
        for name in (
            "pyproject.toml",
            "package.json",
            "backend/pyproject.toml",
            "frontend/package.json",
        )
        if (root / name).is_file()
    ]
    if plan.creation_mode and plan.output_directory:
        base = plan.output_directory
        return BlueprintArtifact(
            repository_type="react-vite-website",
            manifests=manifests,
            architecture=[
                "Deterministisches React-19-/TypeScript-/Vite-Startergerüst als reproduzierbare Build-Pipeline",
                "Semantische, responsive Komponenten statt monolithischer HTML-Datei",
                "Zentrales visuelles System für Farben, Typografie, Abstände und Bewegung",
                "Progressive Animationen mit Reduced-Motion-Alternative",
            ],
            file_plan=[
                BlueprintFile(path=f"{base}/package.json", purpose="Build- und Laufzeitvertrag"),
                BlueprintFile(path=f"{base}/index.html", purpose="Semantischer Vite-Einstieg"),
                BlueprintFile(path=f"{base}/tsconfig.json", purpose="Stabile TypeScript-Projektkonfiguration"),
                BlueprintFile(path=f"{base}/vite.config.ts", purpose="Stabile Vite- und React-Konfiguration"),
                BlueprintFile(path=f"{base}/src/main.tsx", purpose="React-Bootstrap"),
                BlueprintFile(path=f"{base}/src/App.tsx", purpose="Seitenstruktur und Conversion Journey"),
                BlueprintFile(path=f"{base}/src/styles.css", purpose="Designsystem, Responsive Layout und Motion"),
            ],
            test_plan=[
                "npm install und npm run build im erzeugten Produktordner",
                "Statische Prüfung auf Responsive Design und prefers-reduced-motion",
                "Prüfung auf semantische Navigation, Hauptinhalt und klaren CTA",
                "Prüfung auf Platzhaltertexte, fehlende Assets und substanzloses Styling",
            ],
            risks=[
                "Unverifizierte Unternehmensdaten dürfen nicht als Fakten erscheinen",
                "Animationen dürfen Lesbarkeit, Performance und Barrierefreiheit nicht beeinträchtigen",
                "Technisch valide, aber visuell substanzlose Seiten erfüllen die Mission nicht",
            ],
            quality_gates=[
                "react-vite-typescript",
                "content-substance",
                "visual-system",
                "responsive-layout",
                "reduced-motion",
                "conversion-cta",
                "semantic-accessibility",
            ],
        )

    file_plan = [
        BlueprintFile(path=path, purpose="Gezielte Änderung aus Repositoryanalyse")
        for path in plan.expected_files
    ] or [
        BlueprintFile(
            path="Vom Builder nach Code-Suche zu bestimmen",
            purpose="Kleinster sicherer Änderungsumfang",
            required=False,
        )
    ]
    repository_type = (
        "python-typescript-monorepo"
        if any("pyproject" in item for item in manifests)
        and any("package.json" in item for item in manifests)
        else "existing-codebase"
    )
    return BlueprintArtifact(
        repository_type=repository_type,
        manifests=manifests,
        architecture=[
            "Bestehende Modulgrenzen und öffentliche Schnittstellen erhalten",
            "Änderung auf relevante Dateien und vorhandene Konventionen begrenzen",
            "Fehlerpfade und persistente Zustände explizit berücksichtigen",
        ],
        file_plan=file_plan,
        test_plan=[
            "Gezielte Tests für das geänderte Verhalten",
            "Projektweite statische Analyse und Typprüfung",
            "Produktions-Build für betroffene Frontend-Pakete",
        ],
        risks=[
            "Mehrdeutige textbasierte Patches können unbeabsichtigte Stellen ändern",
            "Bestehende API-Verträge und Nutzerdaten müssen kompatibel bleiben",
        ],
        quality_gates=["tests", "lint", "types", "review"],
    )


def _quality_check(name: str, success: bool, output: str) -> dict[str, Any]:
    return {
        "name": name,
        "success": success,
        "output": output,
        "failure_class": None if success else "code",
    }


def validate_product_quality(
    plan: ExecutionPlan,
    workspace: str,
) -> dict[str, Any]:
    """Run deterministic product gates against the generated product itself."""
    if not plan.creation_mode or not plan.output_directory:
        return {"success": True, "checks": []}

    product = resolve_workspace_path(workspace, plan.output_directory, must_exist=True)
    sources: dict[str, str] = {}
    for path in product.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".md"
        }:
            continue
        try:
            sources[path.relative_to(product).as_posix()] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
    combined = "\n".join(sources.values())
    lower = combined.lower()
    try:
        package = json.loads(sources.get("package.json", "{}"))
    except json.JSONDecodeError:
        package = {}
    dependencies = {
        **package.get("dependencies", {}),
        **package.get("devDependencies", {}),
    }
    scripts = package.get("scripts", {})
    css = "\n".join(text for name, text in sources.items() if name.endswith((".css", ".scss")))
    markup = "\n".join(text for name, text in sources.items() if name.endswith((".html", ".jsx", ".tsx")))
    checks = [
        _quality_check(
            "product-required-files",
            all(
                required in sources
                for required in ("package.json", "index.html", "src/main.tsx", "src/App.tsx")
            ),
            "package.json, index.html, src/main.tsx und src/App.tsx sind erforderlich.",
        ),
        _quality_check(
            "product-react-vite-typescript",
            "react" in dependencies and "vite" in dependencies
            and any(name.endswith(".tsx") for name in sources) and "build" in scripts,
            "React, Vite, TypeScript und ein Build-Script sind verbindlich.",
        ),
        _quality_check(
            "product-no-placeholder-content",
            not re.search(r"\b(lorem ipsum|todo content|placeholder|unternehmen [ab])\b", lower),
            "Keine Lorem-, TODO-, generischen Placeholder- oder Unternehmen-A/B-Texte.",
        ),
        _quality_check(
            "product-content-substance",
            len(re.sub(r"[<>{};:=/\-\s]", "", markup)) >= 500,
            "Die Website benötigt eine substanzielle Seiten- und Content-Struktur.",
        ),
        _quality_check(
            "product-visual-system",
            len(css) >= 800 and (":root" in css or "--" in css)
            and any(token in css for token in ("grid", "flex")),
            "Mindestens 800 Zeichen CSS, Design Tokens und ein echtes Layoutsystem erforderlich.",
        ),
        _quality_check(
            "product-responsive-layout",
            "@media" in css and any(token in css for token in ("max-width", "min-width")),
            "Mindestens ein responsiver Breakpoint ist erforderlich.",
        ),
        _quality_check(
            "product-reduced-motion",
            "prefers-reduced-motion" in css,
            "Animationen benötigen eine prefers-reduced-motion-Alternative.",
        ),
        _quality_check(
            "product-motion-design",
            any(token in css for token in ("@keyframes", "animation:", "transition:", "scroll-behavior")),
            "Das gewünschte Motion-Konzept muss technisch umgesetzt sein.",
        ),
        _quality_check(
            "product-conversion-cta",
            bool(re.search(r"<(?:a|button)\b", markup, re.IGNORECASE))
            and bool(re.search(r"kontakt|anfragen|termin|angebot|start", markup, re.IGNORECASE)),
            "Ein semantischer, klar beschrifteter Conversion-CTA ist erforderlich.",
        ),
        _quality_check(
            "product-semantic-accessibility",
            all(re.search(pattern, markup, re.IGNORECASE) for pattern in (r"<nav\b", r"<main\b", r"<h1\b")),
            "Navigation, main-Inhalt und eine H1 müssen semantisch vorhanden sein.",
        ),
    ]
    return {"success": all(check["success"] for check in checks), "checks": checks}


def validate_product_build(
    plan: ExecutionPlan,
    workspace: str,
) -> dict[str, Any]:
    """Build the generated product with local dependencies whenever possible."""
    if not plan.creation_mode or not plan.output_directory:
        return {"success": True, "checks": []}

    root = Path(workspace).resolve()
    product = resolve_workspace_path(workspace, plan.output_directory, must_exist=True)
    package_file = product / "package.json"
    if not package_file.is_file():
        return {
            "success": False,
            "checks": [
                _quality_check(
                    "product-build",
                    False,
                    "Produkt-Build nicht möglich: package.json fehlt.",
                )
            ],
        }

    npm = resolve_executable("npm")
    node_modules = product / "node_modules"
    package_lock = product / "package-lock.json"
    had_modules = node_modules.exists()
    had_lock = package_lock.exists()
    linked_modules = False
    checks: list[dict[str, Any]] = []
    try:
        shared_modules = root / "frontend" / "node_modules"
        if not had_modules and shared_modules.is_dir():
            node_modules.symlink_to(shared_modules, target_is_directory=True)
            linked_modules = True
            checks.append(
                _quality_check(
                    "product-dependencies",
                    True,
                    "Lokale Mission-Control-Dependencies für den isolierten Build verwendet.",
                )
            )
        elif not had_modules:
            try:
                installed, install_output = run_command(
                    [
                        npm,
                        "install",
                        "--ignore-scripts",
                        "--no-audit",
                        "--no-fund",
                        "--prefer-offline",
                    ],
                    cwd=product,
                    timeout=300,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                installed, install_output = False, str(exc)
            checks.append(
                {
                    "name": "product-dependencies",
                    "success": installed,
                    "output": install_output[-5_000:],
                    "failure_class": "infrastructure" if not installed else None,
                }
            )
            if not installed:
                return {"success": False, "checks": checks}

        failure_class: str | None
        try:
            built, build_output = run_command(
                [npm, "run", "build"],
                cwd=product,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            built, build_output = False, str(exc)
            failure_class = "infrastructure"
        else:
            failure_class = "code" if not built else None
        checks.append(
            {
                "name": "product-build",
                "success": built,
                "output": build_output[-8_000:] or "Produktions-Build erfolgreich.",
                "failure_class": failure_class,
            }
        )
        return {"success": all(check["success"] for check in checks), "checks": checks}
    finally:
        if linked_modules and node_modules.is_symlink():
            node_modules.unlink()
        elif not had_modules and node_modules.exists():
            shutil.rmtree(node_modules)
        if not had_lock and package_lock.exists():
            package_lock.unlink()


def create_release_candidate(
    *, run_id: str, task: str, paths: list[str], validation: dict[str, Any], summary: str
) -> dict[str, Any]:
    gate_lines = [
        f"- {check['name']}: {'bestanden' if check['success'] else 'fehlgeschlagen'}"
        for check in validation.get("checks", [])
    ]
    commit_subject = re.sub(r"\s+", " ", task).strip()[:64]
    markdown = "\n".join([
        f"# Release Candidate {run_id[:8]}", "", f"## Auftrag\n\n{task}",
        f"## Ergebnis\n\n{summary or 'Implementierung abgeschlossen.'}",
        "## Geänderte Dateien", *(f"- `{path}`" for path in paths), "",
        "## Qualitätsgates", *(gate_lines or ["- Keine projektspezifischen Commands konfiguriert."]), "",
    ])
    return {
        "artifact_type": "release_candidate", "version": "1.0", "status": "ready",
        "commit_message": f"feat: {commit_subject or 'complete mission'}",
        "changed_files": paths,
        "quality_gate_count": len(validation.get("checks", [])),
        "quality_gates_passed": all(check.get("success") for check in validation.get("checks", [])),
        "release_notes": markdown,
    }
