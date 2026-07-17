from __future__ import annotations

import json
import time
from typing import Any

from backend.app.core.workspace_security import (
    relative_workspace_path,
    resolve_workspace_path,
)
from backend.app.services.agent_catalog import STEP_TO_AGENT
from backend.app.services.agent_team import agent_team
from backend.app.services.coder import execute_plan
from backend.app.services.engineering_quality import (
    create_react_vite_scaffold,
    create_release_candidate,
    create_technical_blueprint,
    validate_product_build,
    validate_product_quality,
)
from backend.app.services.github_publisher import github_publisher
from backend.app.services.planner import create_execution_plan
from backend.app.services.run_service import run_service
from backend.app.services.reviewer import review_changes
from backend.app.services.validator import validate_project
from backend.app.services.workspace_sandbox import prepare_isolated_workspace


class RunCancelled(RuntimeError):
    pass


class RunLimitExceeded(RuntimeError):
    pass


class AutonomousRunEngine:
    _SCAFFOLD_OWNED_PATHS = {
        "index.html",
        "package.json",
        "tsconfig.json",
        "tsconfig.app.json",
        "tsconfig.node.json",
        "vite.config.ts",
        "src/main.tsx",
        "src/vite-env.d.ts",
        "src/App.tsx",
        "src/styles.css",
    }

    def _assert_product_path_is_customizable(self, plan: Any, path: str) -> None:
        output_directory = (plan.output_directory or "").rstrip("/")
        prefix = f"{output_directory}/"
        relative = path[len(prefix):] if path.startswith(prefix) else path
        if relative in self._SCAFFOLD_OWNED_PATHS:
            raise ValueError(
                f"{path} gehört zum deterministischen Startergerüst und darf von "
                "BUILDER nicht verändert werden. Individualisiere src/content.ts, "
                "src/theme.css, Komponenten oder Assets."
            )

    def _creation_files(
        self,
        plan: Any,
        workspace: str,
        coder_result: dict[str, Any],
    ) -> list[dict[str, str]]:
        output_directory = (plan.output_directory or "").rstrip("/")
        files_by_path = {
            item["path"]: item for item in coder_result.get("files", [])
        }
        for edit in coder_result.get("edits", []):
            path = edit["path"]
            target = resolve_workspace_path(workspace, path)
            if not target.exists() and path not in files_by_path:
                files_by_path[path] = {
                    "path": path,
                    "content": edit.get("replacement", ""),
                }
        files = list(files_by_path.values())
        if not files and not coder_result.get("edits"):
            raise ValueError("Produktmodus benötigt mindestens eine neue Datei.")
        invalid = [
            item["path"]
            for item in files
            if not output_directory
            or not item["path"].startswith(f"{output_directory}/")
        ]
        if invalid:
            raise ValueError(
                "Produktdateien müssen im vorgesehenen Projektordner liegen: "
                + ", ".join(invalid)
            )
        for item in files:
            self._assert_product_path_is_customizable(plan, item["path"])
        return files

    def _creation_edits(
        self,
        plan: Any,
        workspace: str,
        coder_result: dict[str, Any],
        *,
        full_replacement: bool = False,
    ) -> list[dict[str, Any]]:
        """Keep repair edits for files that already exist inside the product root."""
        if full_replacement:
            return []
        output_directory = (plan.output_directory or "").rstrip("/")
        replacement_paths = {
            item["path"] for item in coder_result.get("files", [])
        }
        edits: list[dict[str, Any]] = []
        for item in coder_result.get("edits", []):
            path = item["path"]
            if not output_directory or not path.startswith(f"{output_directory}/"):
                raise ValueError(
                    "Produkt-Edits müssen im vorgesehenen Projektordner liegen: " + path
                )
            self._assert_product_path_is_customizable(plan, path)
            if path in replacement_paths:
                continue
            if resolve_workspace_path(workspace, path).exists():
                edits.append(item)
        return edits

    @staticmethod
    def _failure_signature(failure: dict[str, Any]) -> tuple[str, ...]:
        return tuple(
            sorted(
                str(check.get("name", "unknown"))
                for check in failure.get("checks", [])
                if not check.get("success")
            )
        )

    @staticmethod
    def _repair_feedback(
        failure: dict[str, Any],
        *,
        repeated: bool = False,
    ) -> str:
        failed = [
            check for check in failure.get("checks", []) if not check.get("success")
        ]
        lines = ["Behebe ausschließlich diese fehlgeschlagenen Gates:"]
        for check in failed:
            output = " ".join(str(check.get("output", "")).split())[-1_200:]
            lines.append(f"- {check.get('name', 'unknown')}: {output}")
        if repeated:
            lines.extend(
                [
                    "STRATEGIEWECHSEL: Derselbe Gate-Satz ist erneut fehlgeschlagen.",
                    "Ersetze ausschließlich betroffene individualisierbare Dateien wie src/content.ts oder src/theme.css vollständig über `files`, statt das Fundament nachzubauen.",
                    "Erhalte das von Mission Control bereitgestellte Inhalts-Schema in src/content.ts vollständig und ändere nur dessen Werte.",
                    "package.json, index.html, TypeScript-/Vite-Konfiguration, src/main.tsx, src/App.tsx und src/styles.css gehören Mission Control und dürfen nie ausgegeben werden.",
                ]
            )
        return "\n".join(lines)[-6_000:]

    def _activate_agent(self, run_id: str, status: str, agent: str) -> None:
        current = run_service.get(run_id)
        previous = current.get("current_step") if current else None
        previous_role = STEP_TO_AGENT.get(previous, previous) if previous else None
        next_role = STEP_TO_AGENT.get(agent, agent)
        if previous_role and previous_role != next_role:
            agent_team.complete_assignments(run_id, previous_role)
            task = current.get("task", "Run fortsetzen") if current else "Run fortsetzen"
            delegations = agent_team.handoff(run_id, previous_role, next_role, task)
            for delegation in delegations:
                run_service.add_event(run_id, "agent.delegated", delegation)
            agent_team.remember(
                previous_role,
                f"Aufgabe an {next_role} übergeben: {task}",
                kind="handoff",
                run_id=run_id,
            )
            run_service.add_event(
                run_id,
                "agent.completed",
                {"agent": previous_role},
            )
            run_service.add_event(
                run_id,
                "agent.handoff",
                {"from": previous_role, "to": next_role},
            )
        run_service.transition(run_id, status, agent)
        if previous_role != next_role:
            task = current.get("task", "Run ausführen") if current else "Run ausführen"
            agent_team.remember(
                next_role,
                f"Aufgabe übernommen: {task}",
                kind="assignment",
                run_id=run_id,
            )
            run_service.add_event(run_id, "agent.started", {"agent": next_role})

    def _complete_agent(self, run_id: str) -> None:
        current = run_service.get(run_id)
        if current and current.get("current_step"):
            agent = STEP_TO_AGENT.get(
                current["current_step"], current["current_step"]
            )
            agent_team.complete_assignments(run_id, agent)
            run_service.add_event(
                run_id,
                "agent.completed",
                {"agent": agent},
            )
            agent_team.remember(
                agent,
                "Agentenschritt erfolgreich abgeschlossen.",
                kind="result",
                run_id=run_id,
            )

    def _guard(self, run_id: str, started_at: float) -> dict[str, Any]:
        run = run_service.get(run_id)
        if run is None or run["cancel_requested"]:
            raise RunCancelled("Run wurde abgebrochen.")
        if time.monotonic() - started_at > run["limits"]["timeout_seconds"]:
            raise RunLimitExceeded("Maximale Laufzeit überschritten.")
        if run["tool_calls"] >= run["limits"]["max_tool_calls"]:
            raise RunLimitExceeded("Maximale Anzahl Tool-Aufrufe überschritten.")
        return run

    def _tool_event(self, run_id: str, name: str, payload: Any) -> None:
        current = run_service.get(run_id)
        if current is None:
            raise KeyError(run_id)
        run_service.update(run_id, tool_calls=current["tool_calls"] + 1)
        run_service.add_event(
            run_id, "tool.completed", {"tool": name, "result": payload}
        )

    def _schedule_repair(self, run_id: str, failure: dict[str, Any]) -> str:
        current = run_service.get(run_id)
        if current is None:
            raise KeyError(run_id)
        if current["repair_attempts"] >= current["limits"]["max_repair_attempts"]:
            run_service.add_event(
                run_id,
                "repair.exhausted",
                {"attempts": current["repair_attempts"], "failure": failure},
            )
            raise RuntimeError("Reparaturversuche ausgeschöpft.")
        attempts = current["repair_attempts"] + 1
        run_service.update(run_id, repair_attempts=attempts)
        run_service.add_event(run_id, "repair.started", {"attempt": attempts})
        return json.dumps(failure, ensure_ascii=False)[-30_000:]

    def _apply_files(
        self,
        run_id: str,
        workspace: str,
        files: list[dict[str, str]],
        originals: dict[str, str | None],
    ) -> list[str]:
        changed: list[str] = []
        for item in files:
            target = resolve_workspace_path(workspace, item["path"])
            relative = relative_workspace_path(workspace, target)
            if relative not in originals:
                originals[relative] = (
                    target.read_text(encoding="utf-8") if target.exists() else None
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item["content"], encoding="utf-8")
            changed.append(relative)
            self._tool_event(run_id, "write_file", {"path": relative})
        return changed

    def _apply_edits(
        self,
        run_id: str,
        workspace: str,
        edits: list[dict[str, Any]],
        originals: dict[str, str | None],
    ) -> list[str]:
        # Apply the complete model response as one transaction in memory first.
        # A later ambiguous edit must never leave earlier edits half-applied.
        staged: dict[str, tuple[Any, str]] = {}
        changed: list[str] = []
        for item in edits:
            target = resolve_workspace_path(workspace, item["path"])
            relative = relative_workspace_path(workspace, target)
            search = item["search"]

            if not target.exists():
                if search:
                    raise ValueError(
                        "Datei existiert nicht und kann nur mit leerem `search` "
                        f"neu erstellt werden: {relative}"
                    )
                if relative not in originals:
                    originals[relative] = None
                staged[relative] = (target, item["replacement"])
                changed.append(relative)
                continue

            staged_item = staged.get(relative)
            current = (
                staged_item[1]
                if staged_item is not None
                else target.read_text(encoding="utf-8")
            )
            count = current.count(search) if search else 0
            occurrence = item.get("occurrence")
            if count == 1:
                updated = current.replace(search, item["replacement"], 1)
            elif count > 1 and isinstance(occurrence, int) and 1 <= occurrence <= count:
                start = -1
                for _ in range(occurrence):
                    start = current.find(search, start + 1)
                updated = (
                    current[:start]
                    + item["replacement"]
                    + current[start + len(search) :]
                )
            else:
                raise ValueError(
                    "Patch-Suchtext muss exakt einmal vorkommen oder eine gültige "
                    f"occurrence angeben: {relative} (Vorkommen: {count})"
                )
            if relative not in originals:
                originals[relative] = target.read_text(encoding="utf-8")
            staged[relative] = (target, updated)
            changed.append(relative)

        for target, content in staged.values():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for relative in changed:
            self._tool_event(run_id, "apply_edit", {"path": relative})
        return changed

    def _rollback(self, workspace: str, originals: dict[str, str | None]) -> None:
        for relative, content in originals.items():
            target = resolve_workspace_path(workspace, relative)
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_text(content, encoding="utf-8")

    def execute(self, run_id: str) -> None:
        started_at = time.monotonic()
        checkpoint = run_service.load_checkpoint(run_id)
        originals: dict[str, str | None] = checkpoint.get("originals", {})
        changed_paths: set[str] = set(checkpoint.get("changed_paths", []))
        try:
            run = self._guard(run_id, started_at)
            source_workspace = run["source_workspace"]
            sandbox = checkpoint.get("sandbox") or prepare_isolated_workspace(
                source_workspace, run_id
            )
            run_service.update(run_id, workspace=sandbox)
            run_service.save_checkpoint(
                run_id,
                {
                    **checkpoint,
                    "phase": "workspace_prepared",
                    "source_workspace": source_workspace,
                    "sandbox": sandbox,
                    "originals": originals,
                    "changed_paths": sorted(changed_paths),
                },
            )
            run = self._guard(run_id, started_at)
            self._activate_agent(run_id, "planning", "planner")
            plan = create_execution_plan(run["task"], workspace=run["workspace"])
            run_service.update(run_id, plan=plan.model_dump())
            run_service.add_event(run_id, "plan.created", plan.model_dump())
            self._activate_agent(run_id, "planning", "technical_planner")
            blueprint = create_technical_blueprint(plan, run["workspace"])
            if not blueprint.approved:
                raise RuntimeError("BLUEPRINT hat die technische Umsetzung nicht freigegeben.")
            blueprint_payload = blueprint.model_dump()
            run_service.add_event(run_id, "blueprint.created", blueprint_payload)
            run_service.save_checkpoint(
                run_id,
                {
                    "phase": "blueprint_approved",
                    "source_workspace": source_workspace,
                    "sandbox": sandbox,
                    "originals": originals,
                    "changed_paths": sorted(changed_paths),
                    "blueprint": blueprint_payload,
                },
            )

            if plan.creation_mode and plan.output_directory:
                scaffold_files = create_react_vite_scaffold(plan, run["task"])
                changed_paths.update(
                    self._apply_files(
                        run_id,
                        run["workspace"],
                        scaffold_files,
                        originals,
                    )
                )
                scaffold_payload = {
                    "version": "1.0",
                    "stack": "react-vite-typescript",
                    "root": plan.output_directory,
                    "files": [item["path"] for item in scaffold_files],
                }
                run_service.add_event(
                    run_id,
                    "product.scaffold.created",
                    scaffold_payload,
                )
                run_service.save_checkpoint(
                    run_id,
                    {
                        "phase": "product_scaffold_created",
                        "source_workspace": source_workspace,
                        "sandbox": sandbox,
                        "originals": originals,
                        "changed_paths": sorted(changed_paths),
                        "blueprint": blueprint_payload,
                        "scaffold": scaffold_payload,
                    },
                )

            feedback = ""
            validation: dict[str, Any] = {"success": False, "checks": []}
            summary = ""
            failure_counts: dict[tuple[str, ...], int] = {}
            last_validation_failure: dict[str, Any] = {"success": False, "checks": []}
            while True:
                run = self._guard(run_id, started_at)
                self._activate_agent(run_id, "executing", "coder")
                coder_result = execute_plan(
                    plan,
                    run["workspace"],
                    feedback,
                    blueprint,
                )
                self._tool_event(
                    run_id, "ollama.generate", {"status": coder_result["status"]}
                )
                if coder_result.get("status") != "completed":
                    raise RuntimeError(
                        coder_result.get("error", "Coder fehlgeschlagen.")
                    )
                summary = coder_result.get("summary", "")
                try:
                    if plan.creation_mode:
                        repair_edits = self._creation_edits(
                            plan,
                            run["workspace"],
                            coder_result,
                            full_replacement="STRATEGIEWECHSEL" in feedback,
                        )
                        changed_paths.update(
                            self._apply_files(
                                run_id,
                                run["workspace"],
                                self._creation_files(
                                    plan, run["workspace"], coder_result
                                ),
                                originals,
                            )
                        )
                        if repair_edits:
                            changed_paths.update(
                                self._apply_edits(
                                    run_id,
                                    run["workspace"],
                                    repair_edits,
                                    originals,
                                )
                            )
                    elif coder_result.get("edits"):
                        changed_paths.update(
                            self._apply_edits(
                                run_id,
                                run["workspace"],
                                coder_result.get("edits", []),
                                originals,
                            )
                        )
                    if not plan.creation_mode and coder_result.get("files"):
                        changed_paths.update(
                            self._apply_files(
                                run_id,
                                run["workspace"],
                                coder_result.get("files", []),
                                originals,
                            )
                        )
                except (FileNotFoundError, ValueError) as exc:
                    failure = {
                        "success": False,
                        "checks": [
                            {
                                "name": "patch-application",
                                "success": False,
                                "output": str(exc),
                            }
                        ],
                    }
                    run_service.add_event(run_id, "patch.rejected", failure)
                    self._schedule_repair(run_id, failure)
                    signature = self._failure_signature(failure)
                    failure_counts[signature] = failure_counts.get(signature, 0) + 1
                    repeated = (
                        failure_counts[signature] > 1
                        or signature == ("patch-application",)
                    )
                    feedback_failure = failure
                    if signature == ("patch-application",) and last_validation_failure["checks"]:
                        patch_checks = failure.get("checks", [])
                        if not isinstance(patch_checks, list):
                            patch_checks = []
                        feedback_failure = {
                            "success": False,
                            "checks": patch_checks
                            + [
                                    check
                                    for check in last_validation_failure["checks"]
                                    if not check.get("success")
                            ],
                        }
                    feedback = self._repair_feedback(
                        feedback_failure, repeated=repeated
                    )
                    if repeated:
                        run_service.add_event(
                            run_id,
                            "repair.strategy_changed",
                            {"strategy": "replace_target_files", "gates": list(signature)},
                        )
                    continue
                run_service.save_checkpoint(
                    run_id,
                    {
                        "phase": "files_applied",
                        "originals": originals,
                        "changed_paths": sorted(changed_paths),
                    },
                )

                self._guard(run_id, started_at)
                self._activate_agent(run_id, "validating", "validator")
                run_service.add_event(
                    run_id,
                    "validation.phase",
                    {"phase": "product_static", "label": "Produktstruktur prüfen"},
                )
                product_validation = validate_product_quality(plan, run["workspace"])
                product_build: dict[str, Any] = {"success": True, "checks": []}
                repository_validation: dict[str, Any] = {"success": True, "checks": []}
                if product_validation["success"]:
                    run_service.add_event(
                        run_id,
                        "validation.phase",
                        {"phase": "product_build", "label": "Produkt-Build ausführen"},
                    )
                    product_build = validate_product_build(plan, run["workspace"])
                if product_validation["success"] and product_build["success"]:
                    run_service.add_event(
                        run_id,
                        "validation.phase",
                        {"phase": "repository", "label": "Vollständige Merge-Gates prüfen"},
                    )
                    repository_validation = validate_project(run["workspace"])
                validation = {
                    "success": (
                        product_validation["success"]
                        and product_build["success"]
                        and repository_validation["success"]
                    ),
                    "checks": [
                        *product_validation["checks"],
                        *product_build["checks"],
                        *repository_validation["checks"],
                    ],
                }
                self._tool_event(run_id, "validate_project", validation)
                run_service.save_checkpoint(
                    run_id,
                    {
                        "phase": "validated",
                        "originals": originals,
                        "changed_paths": sorted(changed_paths),
                        "validation": validation,
                    },
                )
                infrastructure_failures = [
                    check
                    for check in validation["checks"]
                    if not check["success"]
                    and check.get("failure_class") == "infrastructure"
                ]
                if infrastructure_failures:
                    names = ", ".join(
                        check["name"] for check in infrastructure_failures
                    )
                    run_service.add_event(
                        run_id,
                        "validation.infrastructure_failed",
                        {"checks": names},
                    )
                    raise RuntimeError(
                        "Validierungsinfrastruktur nicht bereit: " + names
                    )
                if validation["success"]:
                    self._activate_agent(run_id, "validating", "reviewer")
                    review = review_changes(run["workspace"], sorted(changed_paths))
                    self._tool_event(run_id, "review_changes", review)
                    if review["approved"]:
                        break
                    validation = {
                        "success": False,
                        "checks": [
                            *validation["checks"],
                            {
                                "name": "reviewer",
                                "success": False,
                                "output": "\n".join(review["issues"]),
                            },
                        ],
                    }

                self._schedule_repair(run_id, validation)
                signature = self._failure_signature(validation)
                failure_counts[signature] = failure_counts.get(signature, 0) + 1
                repeated = failure_counts[signature] > 1
                last_validation_failure = validation
                feedback = self._repair_feedback(validation, repeated=repeated)
                if repeated:
                    run_service.add_event(
                        run_id,
                        "repair.strategy_changed",
                        {"strategy": "replace_target_files", "gates": list(signature)},
                    )

            run = self._guard(run_id, started_at)
            self._activate_agent(run_id, "publishing", "github")
            release_candidate = create_release_candidate(
                run_id=run_id,
                task=run["task"],
                paths=sorted(changed_paths),
                validation=validation,
                summary=summary,
            )
            run_service.add_event(
                run_id,
                "release_candidate.created",
                release_candidate,
            )
            publish_result: dict[str, str] = {}
            if run["publish"]:
                validation_summary = "\n".join(
                    f"- {check['name']}: {'OK' if check['success'] else 'FEHLER'}"
                    for check in validation["checks"]
                )
                publish_result = github_publisher.publish(
                    workspace=run["workspace"],
                    run_id=run_id,
                    task=run["task"],
                    paths=sorted(changed_paths),
                    validation_summary=validation_summary,
                )
                self._tool_event(run_id, "github.publish", publish_result)
                run_service.update(run_id, **publish_result)

            result = {
                "summary": summary,
                "files": sorted(changed_paths),
                "validation": validation,
                "blueprint": blueprint_payload,
                "release_candidate": release_candidate,
                "publish": publish_result or None,
            }
            run_service.update(run_id, result=result)
            self._complete_agent(run_id)
            run_service.transition(run_id, "completed", None)
        except RunCancelled as exc:
            cancelled = run_service.get(run_id)
            self._rollback(cancelled["workspace"], originals)  # type: ignore[index]
            run_service.update(run_id, error=str(exc))
            run_service.transition(
                run_id,
                "cancelled",
                cancelled.get("current_step") if cancelled else None,
            )
        except Exception as exc:
            current = run_service.get(run_id)
            if current is not None:
                self._rollback(current["workspace"], originals)
                run_service.update(run_id, error=str(exc))
                run_service.add_event(run_id, "run.error", {"message": str(exc)})
                run_service.transition(
                    run_id, "failed", current.get("current_step")
                )


run_engine = AutonomousRunEngine()
