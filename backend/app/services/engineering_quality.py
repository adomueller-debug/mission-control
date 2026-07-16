from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.workspace_security import resolve_workspace_path
from backend.app.models.execution_plan import ExecutionPlan


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
                "React 18 mit TypeScript und Vite als reproduzierbare Build-Pipeline",
                "Semantische, responsive Komponenten statt monolithischer HTML-Datei",
                "Zentrales visuelles System für Farben, Typografie, Abstände und Bewegung",
                "Progressive Animationen mit Reduced-Motion-Alternative",
            ],
            file_plan=[
                BlueprintFile(path=f"{base}/package.json", purpose="Build- und Laufzeitvertrag"),
                BlueprintFile(path=f"{base}/index.html", purpose="Semantischer Vite-Einstieg"),
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
