from __future__ import annotations

import json
import os
import re

import requests
from pydantic import BaseModel, Field, ValidationError, model_validator

from backend.app.models.execution_plan import ExecutionPlan
from backend.app.services.engineering_quality import BlueprintArtifact
from backend.app.services.workspace_context import load_workspace_context

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_CONTEXT = int(os.getenv("OLLAMA_CONTEXT", "8192"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "4096"))


class GeneratedEdit(BaseModel):
    path: str
    search: str
    replacement: str
    occurrence: int | None = Field(
        default=None,
        ge=1,
        description=(
            "1-basierte Vorkommensnummer, aber nur wenn search absichtlich mehrfach "
            "vorkommt; sonst null"
        ),
    )


class GeneratedFile(BaseModel):
    path: str
    content: str


class CoderOutput(BaseModel):
    summary: str
    edits: list[GeneratedEdit] = Field(default_factory=list, max_length=8)
    files: list[GeneratedFile] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def require_change(self) -> "CoderOutput":
        if not self.edits and not self.files:
            raise ValueError("Mindestens eine Änderung oder neue Datei ist erforderlich.")
        return self


def _parse_output(raw: str) -> CoderOutput:
    without_thinking = re.sub(
        r"<think>.*?</think>",
        "",
        raw,
        flags=re.DOTALL,
    ).strip()
    cleaned = re.sub(
        r"^```(?:json)?\\s*|\\s*```$",
        "",
        without_thinking,
    )
    try:
        start = cleaned.find("{")
        if start < 0:
            raise ValueError("JSON-Objekt fehlt")
        payload, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        return CoderOutput.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise ValueError(
            f"LLM-Ausgabe passt nicht zum Coding-Schema: {exc}"
        ) from exc


def execute_plan(
    plan: ExecutionPlan,
    workspace: str | None = None,
    feedback: str = "",
    blueprint: BlueprintArtifact | dict | None = None,
) -> dict:
    context_files = list(plan.expected_files)
    if plan.creation_mode:
        blueprint_files = (
            [item.path for item in blueprint.file_plan]
            if isinstance(blueprint, BlueprintArtifact)
            else [
                str(item.get("path", ""))
                for item in (blueprint or {}).get("file_plan", [])
                if isinstance(item, dict)
            ]
        )
        context_files.extend(path for path in blueprint_files if path)
    workspace_context = load_workspace_context(
        list(dict.fromkeys(context_files)), workspace
    )
    full_replacement_mode = "STRATEGIEWECHSEL" in feedback
    scope_instruction = (
        f"Erstelle ein eigenständiges neues Produkt ausschließlich unter "
        f"`{plan.output_directory}/`. Nutze dafür `files`; ändere keine bestehenden "
        "Mission-Control-Dateien. Erzeuge ein professionelles, vollständiges React-/Vite-/"
        "TypeScript-Produkt mit Komponenten, substanziellen Inhalten, responsivem Design, "
        "Design Tokens, hochwertiger Typografie, klarer Conversion Journey und dynamischen "
        "Animationen samt Reduced-Motion-Alternative. Eine einfache HTML-Demoseite ist "
        "nicht ausreichend."
        if plan.creation_mode and plan.output_directory
        else "Ändere nur die für das Ziel erforderlichen bestehenden Dateien."
    )
    prompt = f"""
Du bist ein Senior Software Engineer. Arbeite den Plan vollständig ab.

Ziel:
{plan.goal}

Schritte:
{json.dumps([step.model_dump() for step in plan.steps], indent=2, ensure_ascii=False)}

Workspace-Kontext:
{workspace_context or "Keine bestehenden Dateien als Kontext vorhanden."}

Validierungsfeedback:
{feedback or "Noch keine Validierung ausgeführt."}

Verbindliches BLUEPRINT-Artefakt:
{json.dumps(blueprint.model_dump() if isinstance(blueprint, BlueprintArtifact) else blueprint or {}, indent=2, ensure_ascii=False)}

Arbeitsmodus:
{scope_instruction}

Setze den Dateiplan und alle Quality Gates aus BLUEPRINT vollständig um. Wenn der Plan ein
React-/Vite-/TypeScript-Produkt fordert, müssen package.json, index.html, TypeScript-Einstieg,
komponentenbasierte App und ein substanzielles Stylesheet direkt buildbar geliefert werden.

Erzeuge höchstens acht präzise Edits oder zwölf kompakte neue Dateien.
Für jede Änderung soll `search` exakt einmal im aktuellen Dateiinhalt vorkommen.
Verwende bei wiederholten Assertions oder Blöcken ausreichend langen umgebenden Kontext,
damit der Suchtext eindeutig ist. Beachte das Validierungsfeedback exakt.
Falls ein Reviewer ausdrücklich eines von mehreren identischen Vorkommen beanstandet und
ein längerer eindeutiger Kontext unmöglich ist, setze `occurrence` auf dessen 1-basierte
Position. Verwende `occurrence` niemals, um eine unbeabsichtigt mehrdeutige Änderung zu
erzwingen.
`replacement` ersetzt diesen Text vollständig. Gib niemals komplette unveränderte Dateien aus.
Verwende `edits` ausschließlich für Dateien, die bereits im Workspace existieren.
Verwende `files` für jede neue Datei und liefere dort den vollständigen Dateiinhalt. Im
Produktmodus darf `files` bei einer ausdrücklich verlangten Vollersatz-Reparatur auch eine
bestehende Datei vollständig ersetzen.
{
    "REPARATURMODUS VOLLERSATZ: `edits` muss leer bleiben. Liefere jede betroffene Datei "
    "mit vollständigem Inhalt in `files`; insbesondere auch package.json und Stylesheets."
    if full_replacement_mode
    else ""
}
Antworte ausschließlich im vorgegebenen JSON-Schema.
Erzeuge mindestens einen Eintrag in `edits` oder `files`.
Gib keine Markdown-Codeblöcke und keine zusätzliche Erklärung aus.
JSON-Schema:
{json.dumps(CoderOutput.model_json_schema(), ensure_ascii=False)}
"""
    raw = ""
    last_error = ""
    result: CoderOutput | None = None
    for attempt in range(2):
        retry_note = (
            "\nDeine vorherige Antwort war kein gültiges Schema. Antworte jetzt ohne "
            "Erklärung ausschließlich mit einem vollständigen JSON-Objekt."
            if attempt
            else ""
        )
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt + retry_note,
                "stream": False,
                "think": False,
                "format": CoderOutput.model_json_schema(),
                "keep_alive": "30m",
                "options": {
                    "num_ctx": OLLAMA_CONTEXT,
                    "num_predict": OLLAMA_MAX_TOKENS,
                    "temperature": 0.05 if attempt else 0.1,
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        raw = response.json()["response"]
        try:
            result = _parse_output(raw)
            break
        except ValueError as exc:
            last_error = str(exc)
            continue
    if result is None:
        return {
            "status": "failed",
            "error": "Ollama lieferte zweimal kein gültiges Coding-JSON.",
            "diagnostic": raw[:1000],
            "parse_error": last_error,
        }
    return {
        "status": "completed",
        "summary": result.summary,
        "edits": [edit.model_dump() for edit in result.edits],
        "files": [item.model_dump() for item in result.files],
    }
