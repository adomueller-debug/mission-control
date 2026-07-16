import subprocess


def run_tool(command: str) -> str:
    try:
        result = subprocess.check_output(
            command, shell=True, stderr=subprocess.STDOUT, text=True
        )
        return result
    except Exception as e:
        return str(e)
