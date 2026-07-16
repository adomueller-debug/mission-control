from __future__ import annotations


class ReflectionEngine:
    def reflect(self, results: list[dict]) -> dict:
        if not results:
            return {
                "status": "need_more_context",
                "reason": "Keine Ergebnisse vorhanden.",
            }

        last = results[-1]

        if last["tool"] == "read_file":
            return {
                "status": "ready",
                "reason": "Genug Kontext vorhanden.",
            }

        return {
            "status": "continue",
            "reason": "Weitere Tools erforderlich.",
        }


reflection_engine = ReflectionEngine()
