from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.mission_control import router as mission_control_router
from backend.app.api.files import router as files_router
from backend.app.api.patches import router as patches_router
from backend.app.api.ws import router as ws_router
from backend.app.api.planner import router as planner_router
from backend.app.api.orchestrator import router as orchestrator_router
from backend.app.api.coder import router as coder_router
from backend.app.api.workflow import router as workflow_router
from backend.app.api.validator import router as validator_router
from backend.app.api.index import router as index_router
from backend.app.api.symbols import router as symbols_router
from backend.app.api.search import router as search_router
from backend.app.api.coding import router as coding_router
from backend.app.api.health import router as health_router
from backend.app.api.runs import router as runs_router
from backend.app.api.projects import router as projects_router
from backend.app.api.integrations import router as integrations_router
from backend.app.api.missions import router as missions_router
from backend.app.api.operations import router as operations_router
from backend.app.api.sales import router as sales_router
from backend.app.api.v2 import router as v2_router

from backend.app.database.database import Base, engine
from backend.app.api.tasks import router as tasks_router
from backend.app.api.agents import router as agents_router
from backend.app.models.run import AgentRun, RunCheckpoint, RunEvent  # noqa: F401
from backend.app.models.project import Project, ProjectArtifact, ProjectTask  # noqa: F401
from backend.app.models.mission import (  # noqa: F401
    IntegrationRequirement,
    MissionPlan,
    MissionPlanTask,
)
from backend.app.models.mission_v2 import (  # noqa: F401
    AgentAssignment,
    Approval,
    AuditedToolCall,
    CostEntry,
    Mission,
    QualityGate,
    ResourceLease,
    WorkItem,
)
from backend.app.core.version import MISSION_CONTROL_VERSION
from backend.app.services.run_service import run_service
from backend.app.services.project_service import project_service
from backend.app.services.mission_scheduler_v2 import mission_scheduler_v2

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("MISSION_CONTROL_TESTING") != "1":
        run_service.resume_incomplete()
        project_service.recover_autopilots()
        mission_scheduler_v2.recover()
    yield


app = FastAPI(
    title="Mission Control",
    version=MISSION_CONTROL_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(tasks_router, prefix="/legacy", deprecated=True)
app.include_router(agents_router, prefix="/legacy", deprecated=True)


@app.get("/")
def root():
    return {"status": "running", "version": MISSION_CONTROL_VERSION}


app.include_router(health_router)
app.include_router(runs_router)
app.include_router(projects_router)
app.include_router(integrations_router)
app.include_router(missions_router)
app.include_router(operations_router)
app.include_router(sales_router)
app.include_router(v2_router)

# Temporäre Kompatibilität für den früheren, nicht mehr kanonischen API-Pfad.
for legacy_router in (
    coding_router,
    mission_control_router,
    files_router,
    patches_router,
    ws_router,
    planner_router,
    orchestrator_router,
    coder_router,
    workflow_router,
    validator_router,
    index_router,
    symbols_router,
    search_router,
):
    app.include_router(legacy_router, prefix="/legacy", deprecated=True)
