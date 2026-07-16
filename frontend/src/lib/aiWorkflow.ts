import { useFileStore } from "./fileStore";
import { usePatchStore } from "./patchStore";

export async function createPatchFromCurrentFile() {
  const { selectedFile, content } = useFileStore.getState();

  if (!selectedFile) {
    throw new Error("Keine Datei geöffnet.");
  }

  await usePatchStore.getState().createPatch(
    selectedFile,
    content,
  );
}
