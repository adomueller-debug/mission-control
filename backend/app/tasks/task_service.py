from sqlalchemy.orm import Session

from backend.app.models.task import Task


class TaskService:

    def list(self, db: Session):
        return db.query(Task).all()

    def create(self, db: Session, agent_id: str, instruction: str):
        task = Task(
            agent_id=agent_id,
            instruction=instruction,
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return task


task_service = TaskService()
