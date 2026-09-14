APPROVED_SOURCES = [
    {
        "id": "leave-policy-v1",
        "title": "Leave Policy v1",
        "page": 1,
        "text": "Leave requests must be submitted through the HR portal at least five working days in advance.",
        "keywords": {"leave", "vacation", "absence", "request"},
    }
]


def retrieve_approved_sources(question: str) -> list[dict]:
    terms = set(question.lower().replace("?", "").split())
    return [source for source in APPROVED_SOURCES if terms & source["keywords"]]
