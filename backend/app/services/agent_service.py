from sqlalchemy.orm import Session

from backend.app.models.agent import Agent


class AgentService:

    def list(self, db: Session):
        return db.query(Agent).all()

    def get(self, db: Session, agent_id: str):
        return db.query(Agent).filter(Agent.id == agent_id).first()

    def create(self, db: Session, name: str, description: str):
        agent = Agent(
            name=name,
            description=description,
        )

        db.add(agent)
        db.commit()
        db.refresh(agent)

        return agent

    def delete(self, db: Session, agent_id: str):
        agent = self.get(db, agent_id)

        if agent is None:
            return None

        db.delete(agent)
        db.commit()

        return agent


agent_service = AgentService()
