from src.agents.orchestrator import TrainingOrchestrator


def route_question(question: str, orchestrator: TrainingOrchestrator | None = None) -> dict:
    state = (orchestrator or TrainingOrchestrator()).run(question)
    return {
        "answer": state.answer,
        "citations": state.citations,
        "out_of_scope": state.out_of_scope,
    }
