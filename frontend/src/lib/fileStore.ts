import { create } from "zustand";

type FileState = {
  selectedFile: string | null;
  content: string;
  openFile: (path: string) => Promise<void>;
};

export const useFileStore = create<FileState>((set) => ({
  selectedFile: null,
  content: "",

  async openFile(path) {
    const response = await fetch(
      `http://127.0.0.1:8000/files/content?path=${encodeURIComponent(path)}`
    );

    if (!response.ok) return;

    const json = await response.json();

    set({
      selectedFile: json.path,
      content: json.content,
    });
  },
}));
