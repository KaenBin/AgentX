from src.workflows.router import route_question


def test_grounded_question_returns_citation():
    result = route_question("How far in advance must I submit leave?")
    assert "five working days" in result["answer"]
    assert result["citations"][0]["source_id"] == "leave-policy-v1"
    assert result["out_of_scope"] is False


def test_unsupported_question_abstains():
    result = route_question("What is the company stock price?")
    assert result["out_of_scope"] is True
    assert "cannot determine" in result["answer"]
