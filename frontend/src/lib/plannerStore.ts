import { create } from "zustand";

export type PlanStep = {
  id: number;
  title: string;
  description: string;
  agent: string;
  status: string;
};

type PlannerState = {
  goal: string;
  summary: string;
  steps: PlanStep[];
  loading: boolean;
  error: string | null;
  createPlan: (task: string) => Promise<void>;
};

export const usePlannerStore = create<PlannerState>((set) => ({
  goal: "",
  summary: "",
  steps: [],
  loading: false,
  error: null,

  async createPlan(task) {
    set({ loading: true, error: null });

    try {
      const response = await fetch("http://127.0.0.1:8000/planner/plan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ task }),
      });

      if (!response.ok) {
        throw new Error(`Planner API Fehler: ${response.status}`);
      }

      const plan = await response.json();

      set({
        goal: plan.goal,
        summary: plan.summary,
        steps: plan.steps,
        loading: false,
      });
    } catch (error) {
      set({
        loading: false,
        error:
          error instanceof Error ? error.message : "Planner fehlgeschlagen",
      });
    }
  },
}));
