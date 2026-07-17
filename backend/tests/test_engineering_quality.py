from pathlib import Path

from backend.app.models.execution_plan import ExecutionPlan, PlanStep
from backend.app.services import coder as coder_module
from backend.app.services import engineering_quality as quality_module
from backend.app.services.engineering_quality import (
    create_release_candidate,
    create_technical_blueprint,
    validate_product_build,
    validate_product_quality,
)


def website_plan() -> ExecutionPlan:
    return ExecutionPlan(
        goal="Erstelle eine professionelle Website",
        summary="Website",
        creation_mode=True,
        output_directory="projects/acme",
        steps=[
            PlanStep(
                id=1,
                title="Build",
                description="Build website",
                agent="forge_builder",
            )
        ],
    )


def test_blueprint_requires_professional_react_website(tmp_path: Path):
    blueprint = create_technical_blueprint(website_plan(), str(tmp_path))

    assert blueprint.approved is True
    assert blueprint.repository_type == "react-vite-website"
    assert "projects/acme/package.json" in {
        item.path for item in blueprint.file_plan if item.required
    }
    assert "reduced-motion" in blueprint.quality_gates
    assert blueprint.test_plan
    assert blueprint.risks


def test_product_quality_rejects_plain_html_page(tmp_path: Path):
    product = tmp_path / "projects" / "acme"
    product.mkdir(parents=True)
    (product / "index.html").write_text(
        "<html><body><h1>Hallo</h1></body></html>", encoding="utf-8"
    )

    validation = validate_product_quality(website_plan(), str(tmp_path))

    assert validation["success"] is False
    failed = {check["name"] for check in validation["checks"] if not check["success"]}
    assert "product-react-vite-typescript" in failed
    assert "product-visual-system" in failed
    assert "product-reduced-motion" in failed
    assert "product-conversion-cta" in failed


def test_product_quality_accepts_substantive_react_website(tmp_path: Path):
    product = tmp_path / "projects" / "acme"
    source = product / "src"
    source.mkdir(parents=True)
    (product / "package.json").write_text(
        '{"scripts":{"build":"vite build"},"dependencies":{"react":"18"},'
        '"devDependencies":{"vite":"5","typescript":"5"}}',
        encoding="utf-8",
    )
    (product / "index.html").write_text(
        '<html lang="de"><body><div id="root"></div></body></html>',
        encoding="utf-8",
    )
    (source / "main.tsx").write_text("import './styles.css'", encoding="utf-8")
    sections = " ".join(
        f"<section><h2>Leistung {index}</h2><p>{'Qualität und Erfahrung ' * 12}</p></section>"
        for index in range(5)
    )
    (source / "App.tsx").write_text(
        f"<><nav>Navigation</nav><main><h1>Digitale Qualität</h1>{sections}"
        '<a href="#kontakt">Angebot anfragen</a></main></>',
        encoding="utf-8",
    )
    css = """
:root { --ink: #111; --space: 1rem; }
* { box-sizing: border-box; }
body { color: var(--ink); margin: 0; font-family: sans-serif; }
main { display: grid; gap: var(--space); max-width: 80rem; margin: auto; }
section { min-height: 20rem; padding: 4rem; display: flex; transition: transform .4s ease; }
a { display: inline-flex; padding: 1rem 2rem; }
@keyframes reveal { from { opacity: 0; } to { opacity: 1; } }
section { animation: reveal .6s ease both; }
@media (max-width: 48rem) { section { padding: 2rem; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
""" + "\n".join(f".feature-{index} {{ padding: {index + 1}px; }}" for index in range(40))
    (source / "styles.css").write_text(css, encoding="utf-8")

    validation = validate_product_quality(website_plan(), str(tmp_path))

    assert validation["success"] is True
    assert all(check["success"] for check in validation["checks"])


def test_product_build_runs_inside_generated_product(tmp_path: Path, monkeypatch):
    product = tmp_path / "projects" / "acme"
    product.mkdir(parents=True)
    (product / "package.json").write_text(
        '{"scripts":{"build":"vite build"}}', encoding="utf-8"
    )
    shared_modules = tmp_path / "frontend" / "node_modules"
    shared_modules.mkdir(parents=True)
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command, *, cwd=None, timeout=300):
        calls.append((command, Path(cwd)))
        return True, "build ok"

    monkeypatch.setattr(quality_module, "run_command", fake_run)

    validation = validate_product_build(website_plan(), str(tmp_path))

    assert validation["success"] is True
    assert calls == [([quality_module.resolve_executable("npm"), "run", "build"], product)]
    assert not (product / "node_modules").exists()


def test_release_candidate_is_created_without_publishing():
    artifact = create_release_candidate(
        run_id="1234567890",
        task="Improve the dashboard",
        paths=["frontend/src/App.tsx"],
        validation={"checks": [{"name": "build", "success": True}]},
        summary="Dashboard improved",
    )

    assert artifact["status"] == "ready"
    assert artifact["quality_gates_passed"] is True
    assert "Release Candidate 12345678" in artifact["release_notes"]
    assert artifact["changed_files"] == ["frontend/src/App.tsx"]


def test_builder_receives_blueprint_as_binding_context(tmp_path: Path, monkeypatch):
    plan = ExecutionPlan(
        goal="Improve a file",
        summary="Change",
        expected_files=["value.txt"],
        steps=[],
    )
    (tmp_path / "value.txt").write_text("before", encoding="utf-8")
    blueprint = create_technical_blueprint(plan, str(tmp_path))
    captured: dict = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": (
                    '{"summary":"done","edits":[{"path":"value.txt",'
                    '"search":"before","replacement":"after"}],"files":[]}'
                )
            }

    def post(url, *, json, timeout):
        captured.update(json)
        return Response()

    monkeypatch.setattr(coder_module.requests, "post", post)

    result = coder_module.execute_plan(plan, str(tmp_path), blueprint=blueprint)

    assert result["status"] == "completed"
    assert "Verbindliches BLUEPRINT-Artefakt" in captured["prompt"]
    assert "technical_blueprint" in captured["prompt"]
    assert "value.txt" in captured["prompt"]


def test_builder_strategy_switch_requires_full_file_replacement(
    tmp_path: Path, monkeypatch
):
    plan = website_plan()
    captured: dict = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": (
                    '{"summary":"done","edits":[],"files":['
                    '{"path":"projects/acme/package.json","content":"{}"}]}'
                )
            }

    def post(url, *, json, timeout):
        captured.update(json)
        return Response()

    monkeypatch.setattr(coder_module.requests, "post", post)

    result = coder_module.execute_plan(
        plan,
        str(tmp_path),
        feedback="STRATEGIEWECHSEL: vollständiger Ersatz",
    )

    assert result["status"] == "completed"
    assert "`edits` muss leer bleiben" in captured["prompt"]
    assert "insbesondere auch package.json" in captured["prompt"]
