from dataclasses import dataclass, field


@dataclass
class TrainingState:
    question: str
    sources: list[dict] = field(default_factory=list)
    answer: str = ""
    citations: list[dict] = field(default_factory=list)
    out_of_scope: bool = False
