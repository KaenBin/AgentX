from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.workflows.chain import run_training_chain

app = FastAPI(title="Employee Training Assistant", version="0.1.0")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest) -> dict:
    return run_training_chain(request.question)
