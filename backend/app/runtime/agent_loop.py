from backend.app.actions.executor import executor
from backend.app.core.event_logger import event_logger
from backend.app.actions.parser import parser


class AgentLoop:

    def execute(self, planner, context, initial_plan=None):

        history = []

        while True:

            if initial_plan is not None:
                plan = initial_plan
                initial_plan = None
            else:
                plan = planner.execute(context)

            actions = parser.parse(plan)

            if not actions:
                break

            for action in actions:

                event_logger.log(
                    "agent",
                    "action_started",
                    {
                        "tool": action.tool,
                        "operation": action.operation,
                    },
                )

                result = executor.execute(action)

                event_logger.log(
                    "agent",
                    "action_finished",
                    {
                        "tool": action.tool,
                        "operation": action.operation,
                    },
                )

                history.append(
                    {
                        "action": action,
                        "result": result,
                    }
                )

                context.variables["last_result"] = result

            if context.variables.get("finished", False):
                break

        return history


agent_loop = AgentLoop()
