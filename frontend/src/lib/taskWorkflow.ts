import { usePatchStore } from "./patchStore";
import { usePlannerStore } from "./plannerStore";

type WorkflowPatch = {
  path: string;
  content: string;
};

type WorkflowResult = {
  status: string;
  summary: string;
  patches: WorkflowPatch[];
};

export async function startTask(task: string) {
  const response = await fetch(
    "http://127.0.0.1:8000/workflow/execute",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        goal: task,
        summary: "",
        steps: [
          {
            id: 1,
            title: "Implementierung",
            description: task,
            agent: "coder",
            status: "pending",
          },
        ],
        expected_files: [],
      }),
    },
  );

  if (!response.ok) {
    throw new Error(`Workflow fehlgeschlagen: ${response.status}`);
  }

  const workflow = (await response.json()) as WorkflowResult;

  if (workflow.status !== "completed") {
    throw new Error(workflow.summary || "Coder fehlgeschlagen.");
  }

  usePlannerStore.setState({
    goal: task,
    summary: workflow.summary,
    steps: [
      {
        id: 1,
        title: "Implementierung",
        description: workflow.summary,
        agent: "coder",
        status: "completed",
      },
    ],
    loading: false,
    error: null,
  });

  await usePatchStore.getState().createPatches(workflow.patches);
}
