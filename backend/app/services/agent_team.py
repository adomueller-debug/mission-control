from __future__ import annotations

import json
from collections import deque
from typing import Any

from sqlalchemy import select, update

from backend.app.database.database import SessionLocal
from backend.app.models.run import AgentDelegation, AgentMemoryEntry, AgentRun
from backend.app.services.agent_catalog import (
    AGENT_BY_ID,
    can_delegate,
    canonical_agent_id,
    get_agent,
)


def _memory_to_dict(entry: AgentMemoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "agent_id": entry.agent_id,
        "run_id": entry.run_id,
        "kind": entry.kind,
        "content": entry.content,
        "created_at": entry.created_at.isoformat(),
    }


def _delegation_to_dict(delegation: AgentDelegation) -> dict[str, Any]:
    return {
        "id": delegation.id,
        "run_id": delegation.run_id,
        "from_agent": delegation.from_agent,
        "to_agent": delegation.to_agent,
        "task": delegation.task,
        "context": json.loads(delegation.context) if delegation.context else {},
        "status": delegation.status,
        "created_at": delegation.created_at.isoformat(),
    }


class AgentTeamService:
    def remember(
        self,
        agent_id: str,
        content: str,
        *,
        kind: str = "observation",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        if get_agent(agent_id) is None:
            raise ValueError(f"Unbekannter Agent: {agent_id}")
        agent_id = canonical_agent_id(agent_id)
        entry = AgentMemoryEntry(
            agent_id=agent_id,
            run_id=run_id,
            kind=kind,
            content=content.strip(),
        )
        with SessionLocal() as db:
            if run_id and db.get(AgentRun, run_id) is None:
                raise ValueError("Run nicht gefunden")
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return _memory_to_dict(entry)

    def memory(
        self, agent_id: str, *, run_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        if get_agent(agent_id) is None:
            raise ValueError(f"Unbekannter Agent: {agent_id}")
        agent_id = canonical_agent_id(agent_id)
        query = select(AgentMemoryEntry).where(AgentMemoryEntry.agent_id == agent_id)
        if run_id:
            query = query.where(AgentMemoryEntry.run_id == run_id)
        with SessionLocal() as db:
            entries = db.scalars(
                query.order_by(AgentMemoryEntry.created_at.desc()).limit(limit)
            ).all()
            return [_memory_to_dict(entry) for entry in entries]

    def delegate(
        self,
        run_id: str,
        from_agent: str,
        to_agent: str,
        task: str,
        *,
        context: dict[str, Any] | None = None,
        status: str = "queued",
    ) -> dict[str, Any]:
        from_agent = canonical_agent_id(from_agent)
        to_agent = canonical_agent_id(to_agent)
        if not can_delegate(from_agent, to_agent):
            raise ValueError(f"Delegation {from_agent} → {to_agent} ist nicht erlaubt")
        with SessionLocal() as db:
            if db.get(AgentRun, run_id) is None:
                raise ValueError("Run nicht gefunden")
            delegation = AgentDelegation(
                run_id=run_id,
                from_agent=from_agent,
                to_agent=to_agent,
                task=task.strip(),
                context=json.dumps(context or {}, ensure_ascii=False, default=str),
                status=status,
            )
            db.add(delegation)
            db.commit()
            db.refresh(delegation)
            return _delegation_to_dict(delegation)

    def delegations(self, run_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            delegations = db.scalars(
                select(AgentDelegation)
                .where(AgentDelegation.run_id == run_id)
                .order_by(AgentDelegation.created_at)
            ).all()
            return [_delegation_to_dict(item) for item in delegations]

    def complete_assignments(self, run_id: str, agent_id: str) -> int:
        agent_id = canonical_agent_id(agent_id)
        with SessionLocal() as db:
            result = db.execute(
                update(AgentDelegation)
                .where(
                    AgentDelegation.run_id == run_id,
                    AgentDelegation.to_agent == agent_id,
                    AgentDelegation.status == "active",
                )
                .values(status="completed")
            )
            db.commit()
            return int(getattr(result, "rowcount", 0) or 0)

    def delegation_path(self, from_agent: str, to_agent: str) -> list[str]:
        from_agent = canonical_agent_id(from_agent)
        to_agent = canonical_agent_id(to_agent)
        if from_agent == to_agent:
            return [from_agent]
        queue: deque[list[str]] = deque([[from_agent]])
        visited = {from_agent}
        while queue:
            path = queue.popleft()
            current = AGENT_BY_ID.get(path[-1])
            for candidate in current.get("delegates_to", []) if current else []:
                if candidate == to_agent:
                    return [*path, candidate]
                if candidate not in visited:
                    visited.add(candidate)
                    queue.append([*path, candidate])
        raise ValueError(f"Kein Delegationspfad {from_agent} → {to_agent}")

    def handoff(
        self, run_id: str, from_agent: str, to_agent: str, task: str
    ) -> list[dict[str, Any]]:
        path = self.delegation_path(from_agent, to_agent)
        delegations: list[dict[str, Any]] = []
        for index, (source, target) in enumerate(zip(path, path[1:])):
            delegations.append(
                self.delegate(
                    run_id,
                    source,
                    target,
                    task,
                    context={"route": path},
                    status="active" if index == len(path) - 2 else "completed",
                )
            )
        return delegations


agent_team = AgentTeamService()
