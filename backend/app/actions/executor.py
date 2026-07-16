from backend.app.tools.registry import get_tool


class ActionExecutor:

    def execute(self, action):
        tool = get_tool(action.tool)

        aliases = {
            "modify": "edit",
            "update": "edit",
            "replace": "edit",
            "overwrite": "edit",
            "create": "write",
            "append": "write",
        }

        operation_name = aliases.get(
            action.operation,
            action.operation,
        )

        operation = getattr(tool, operation_name)

        arguments = dict(action.arguments)

        argument_aliases = {
            "changes": "content",
            "new_content": "content",
            "text": "content",
            "code": "content",
            "file_path": "path",
            "filepath": "path",
            "filename": "path",
        }

        if operation_name in ("write", "edit"):
            argument_aliases["file"] = "path"

        if operation_name == "edit":
            argument_aliases["source"] = "file"

        normalized = {}

        for key, value in arguments.items():
            normalized[
                argument_aliases.get(key, key)
            ] = value

        return operation(**normalized)


executor = ActionExecutor()
