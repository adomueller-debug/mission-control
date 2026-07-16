from backend.app.core.agent_capability import AgentCapability

CAPABILITIES = {
    "planner": AgentCapability(
        name="planner",
        description="Plans tasks",
        tools=[],
    ),
    "coder": AgentCapability(
        name="coder",
        description="Implements tasks",
        tools=["python", "filesystem", "git"],
    ),
    "analyst": AgentCapability(
        name="analyst",
        description="Reviews implementations",
        tools=["filesystem"],
    ),
}
