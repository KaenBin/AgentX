"""Deterministic course drafting and assessment schema validation."""

import re


def sections(body):
    return [x.strip() for x in re.split(r"\n\s*\n", body) if x.strip()]


def build_course(title, body):
    blocks = sections(body)[:8]
    lessons = []
    questions = []
    for i, b in enumerate(blocks):
        lines = b.splitlines()
        heading = lines[0][:90] if len(lines) > 1 else "Policy point " + str(i + 1)
        fact = " ".join(lines[1:]) if len(lines) > 1 else b
        lessons.append({"title": heading, "text": fact, "source_section": i + 1})
        correct = fact.split(". ")[0].rstrip(".") + "."
        options = [
            correct,
            "Proceed without checking the policy.",
            "Ask a colleague to decide without consulting the policy.",
        ]
        offset = i % 3
        options = options[offset:] + options[:offset]
        questions.append(
            {
                "prompt": "Which action follows the policy for "
                + heading.lower()
                + "?",
                "options": options,
                "answer": options.index(correct),
                "explanation": fact,
                "skill": i,
            }
        )
    assessment = [
        dict(
            q,
            prompt="A colleague needs to act on "
            + lessons[q["skill"]]["title"].lower()
            + ". Which instruction should you give?",
        )
        for q in questions
    ]
    return {
        "lessons": lessons,
        "questions": questions,
        "assessment_questions": assessment,
        "origin": "Extractive draft — trainer review required",
    }


def validate_course(data):
    if not isinstance(data, dict):
        raise ValueError("Course must be an object")
    for bank in ["lessons", "questions", "assessment_questions"]:
        if not isinstance(data.get(bank), list) or not all(
            isinstance(item, dict) for item in data[bank]
        ):
            raise ValueError("Course banks must contain objects")
    if (
        not isinstance(data, dict)
        or not 1 <= len(data.get("lessons", [])) <= 8
        or not 1 <= len(data.get("questions", [])) <= 12
    ):
        raise ValueError("Provide 1–8 lessons and 1–12 questions")
    for l in data["lessons"]:
        if (
            not isinstance(l.get("title"), str)
            or not isinstance(l.get("text"), str)
            or type(l.get("source_section")) is not int
        ):
            raise ValueError("Invalid lesson")
        if not l["title"].strip() or not l["text"].strip():
            raise ValueError("Lessons need a title and text")
    if (
        not isinstance(data.get("assessment_questions"), list)
        or not 1 <= len(data["assessment_questions"]) <= 12
    ):
        raise ValueError("Provide a separate final assessment bank")
    for q in data["questions"] + data["assessment_questions"]:
        if (
            not isinstance(q.get("prompt"), str)
            or not isinstance(q.get("options"), list)
            or not 2 <= len(q["options"]) <= 5
            or not all(isinstance(x, str) for x in q["options"])
        ):
            raise ValueError("Invalid question options")
        if (
            type(q.get("answer")) is not int
            or not 0 <= q["answer"] < len(q["options"])
            or type(q.get("skill")) is not int
            or not 0 <= q["skill"] < len(data["lessons"])
            or not isinstance(q.get("explanation"), str)
        ):
            raise ValueError("Invalid answer key or skill")
        if (
            not q["prompt"].strip()
            or not q["explanation"].strip()
            or any(not x.strip() for x in q["options"])
        ):
            raise ValueError("Questions, options and explanations cannot be blank")
    if {q["prompt"].strip().lower() for q in data["questions"]} & {
        q["prompt"].strip().lower() for q in data["assessment_questions"]
    }:
        raise ValueError("Diagnostic and final prompts must differ")
    if {q["skill"] for q in data["questions"]} != {
        q["skill"] for q in data["assessment_questions"]
    }:
        raise ValueError("Both banks must cover the same skills")
    from src.workflows.readiness_content import validate_readiness
    validate_readiness(data)
    return data
