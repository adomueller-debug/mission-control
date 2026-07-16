import { create } from "zustand";

import { useFileStore } from "./fileStore";

export type PendingPatch = {
  id: string;
  path: string;
  diff: string;
};

type GeneratedFile = {
  path: string;
  content: string;
};

type PatchState = {
  patches: PendingPatch[];
  activeIndex: number;
  loading: boolean;
  error: string | null;

  createPatch: (path: string, content: string) => Promise<void>;
  createPatches: (files: GeneratedFile[]) => Promise<void>;
  applyActivePatch: () => Promise<void>;
  rejectActivePatch: () => Promise<void>;
  selectPatch: (index: number) => void;
};

async function createRemotePatch(
  path: string,
  content: string,
): Promise<PendingPatch> {
  const response = await fetch("http://127.0.0.1:8000/patches/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ path, content }),
  });

  if (!response.ok) {
    throw new Error(`Patch für ${path} fehlgeschlagen: ${response.status}`);
  }

  const patch = await response.json();

  const diffResponse = await fetch(
    `http://127.0.0.1:8000/patches/${patch.patch_id}/diff`,
  );

  if (!diffResponse.ok) {
    throw new Error(`Diff für ${path} fehlgeschlagen: ${diffResponse.status}`);
  }

  const diffResult = await diffResponse.json();

  return {
    id: patch.patch_id,
    path: patch.path,
    diff: diffResult.diff,
  };
}

export const usePatchStore = create<PatchState>((set, get) => ({
  patches: [],
  activeIndex: 0,
  loading: false,
  error: null,

  async createPatch(path, content) {
    set({ loading: true, error: null });

    try {
      const patch = await createRemotePatch(path, content);

      set((state) => ({
        patches: [...state.patches, patch],
        activeIndex: state.patches.length,
        loading: false,
      }));
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Patch fehlgeschlagen",
      });
    }
  },

  async createPatches(files) {
    set({
      loading: true,
      error: null,
      patches: [],
      activeIndex: 0,
    });

    try {
      const patches = [];

      for (const file of files) {
        patches.push(await createRemotePatch(file.path, file.content));
      }

      set({
        patches,
        activeIndex: 0,
        loading: false,
      });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Patches fehlgeschlagen",
      });
    }
  },

  async applyActivePatch() {
    const { patches, activeIndex } = get();
    const patch = patches[activeIndex];

    if (!patch) return;

    const response = await fetch("http://127.0.0.1:8000/patches/apply", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ patch_id: patch.id }),
    });

    if (!response.ok) {
      set({ error: `Übernehmen fehlgeschlagen: ${response.status}` });
      return;
    }

    await useFileStore.getState().openFile(patch.path);

    set((state) => {
      const remaining = state.patches.filter((item) => item.id !== patch.id);

      return {
        patches: remaining,
        activeIndex: Math.min(state.activeIndex, Math.max(remaining.length - 1, 0)),
        error: null,
      };
    });
  },

  async rejectActivePatch() {
    const { patches, activeIndex } = get();
    const patch = patches[activeIndex];

    if (!patch) return;

    const response = await fetch(
      `http://127.0.0.1:8000/patches/${patch.id}`,
      { method: "DELETE" },
    );

    if (!response.ok) {
      set({ error: `Verwerfen fehlgeschlagen: ${response.status}` });
      return;
    }

    set((state) => {
      const remaining = state.patches.filter((item) => item.id !== patch.id);

      return {
        patches: remaining,
        activeIndex: Math.min(state.activeIndex, Math.max(remaining.length - 1, 0)),
        error: null,
      };
    });
  },

  selectPatch(index) {
    set({ activeIndex: index });
  },
}));
