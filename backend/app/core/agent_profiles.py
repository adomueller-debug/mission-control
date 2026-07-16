from backend.app.core.agent_profile import AgentProfile

PLANNER = AgentProfile(
    name="planner", system_prompt="You are an expert planning agent."
)

CODER = AgentProfile(name="coder", system_prompt="You are an expert software engineer.")

ANALYST = AgentProfile(
    name="analyst", system_prompt="You are a senior software reviewer."
)
