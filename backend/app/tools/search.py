from backend.app.indexing.project_index import project_index


class SearchTool:

    def files(self):
        return project_index.python_files()

    def search(self, query: str):
        return project_index.search(query)


search = SearchTool()
