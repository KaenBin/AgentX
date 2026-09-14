from src.core.config import Settings
from src.core.state import TrainingState
from src.tools.db_queries import retrieve_approved_sources
from src.tools.file_ops import read_prompt
from src.agents.worker import GatewayWorker


class TrainingOrchestrator:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.worker = GatewayWorker(self.settings)

    def run(self, question: str) -> TrainingState:
        state = TrainingState(question=question)
        state.sources = retrieve_approved_sources(question)
        state.out_of_scope = not bool(state.sources)
        prompt = read_prompt(self.settings.system_prompt_path)
        state.answer = self.worker.answer(question, state.sources, prompt)
        state.citations = [
            {"source_id": source["id"], "title": source["title"], "page": source["page"]}
            for source in state.sources
        ]
        return state
