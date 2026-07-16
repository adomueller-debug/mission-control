from dataclasses import dataclass, field


@dataclass
class RepositoryMemory:
    visited_files: set[str] = field(default_factory=set)
    modified_files: set[str] = field(default_factory=set)
    failed_files: set[str] = field(default_factory=set)

    def visit(self, path: str):
        self.visited_files.add(path)

    def modified(self, path: str):
        self.modified_files.add(path)

    def failed(self, path: str):
        self.failed_files.add(path)

    def snapshot(self):
        return {
            "visited": sorted(self.visited_files),
            "modified": sorted(self.modified_files),
            "failed": sorted(self.failed_files),
        }


repository_memory = RepositoryMemory()
