from src.workflows.router import route_question


def run_training_chain(question: str) -> dict:
    return route_question(question)
