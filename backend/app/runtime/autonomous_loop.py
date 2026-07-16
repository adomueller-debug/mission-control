from backend.app.services.coding_service import coding_service


class AutonomousLoop:
    def execute(self, path: str, max_iterations: int = 3):
        history = []

        for i in range(max_iterations):
            result = coding_service.improve_file(path)

            history.append({
                "iteration": i + 1,
                "success": result.success,
                "message": result.message,
            })

            if result.success:
                break

        return history


autonomous_loop = AutonomousLoop()
