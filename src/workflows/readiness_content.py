"""Reviewed fictional pilot content, published separately from legacy courses."""

import copy
import json


def pilot_content(course):
    content = copy.deepcopy(course)
    ids = [
        "receipt_evidence",
        "submission_timing",
        "prior_approval",
        "claim_correction",
    ]
    extra = [
        (
            "Your taxi receipt is missing. A colleague suggests attaching only a bank statement. What should you do?",
            [
                "Request a duplicate itemized receipt from the supplier",
                "Use the statement alone",
                "Submit without evidence",
            ],
            0,
        ),
        (
            "A travel expense is 40 calendar days old. What is the next step?",
            [
                "Assume it will be reimbursed",
                "Refer it for manager review",
                "Change the purchase date",
            ],
            1,
        ),
        (
            "A team member plans a SGD 300 purchase. Which action meets the procedure?",
            [
                "Split it into two claims",
                "Buy now and seek approval later",
                "Get written manager approval before buying",
            ],
            2,
        ),
        (
            "Finance asks for a missing attachment on an existing claim. What should the employee do?",
            [
                "Create another claim for the same expense",
                "Correct the existing claim",
                "Ignore the request",
            ],
            1,
        ),
    ]
    objectives = []
    first = [
        (
            "Sam has only a card transaction record for a meal expense. Which step satisfies the receipt rule?",
            [
                "Attach the transaction record alone",
                "Ask the supplier for a duplicate itemized receipt",
                "Remove the evidence field",
            ],
            1,
        ),
        (
            "Lee finds an unsubmitted claim from 32 calendar days ago. What should happen?",
            [
                "Submit it as automatically eligible",
                "Pretend the purchase was yesterday",
                "Refer the late claim for manager review",
            ],
            2,
        ),
        (
            "A work purchase will cost SGD 220. What must happen before the purchase?",
            [
                "Obtain written manager approval",
                "Wait for Finance to reimburse it",
                "Seek approval only if a receipt is lost",
            ],
            0,
        ),
        (
            "An expense claim is returned because a required document is missing. Which response follows the policy?",
            [
                "Correct that claim with the document",
                "Submit the same expense again",
                "Ignore Finance's request",
            ],
            0,
        ),
    ]
    for i, lesson in enumerate(content["lessons"]):
        second = dict(
            prompt=extra[i][0],
            options=extra[i][1],
            answer=extra[i][2],
            explanation=lesson["text"],
            skill=i,
        )
        objectives.append(
            {
                "id": ids[i],
                "title": lesson["title"],
                "critical": i < 3,
                "source_section": lesson["source_section"],
                "lesson": lesson["text"],
                "diagnostic": dict(content["questions"][i], id=ids[i] + "_diagnostic"),
                "reassessments": [
                    dict(
                        prompt=first[i][0],
                        options=first[i][1],
                        answer=first[i][2],
                        explanation=lesson["text"],
                        skill=i,
                        id=ids[i] + "_case_1",
                    ),
                    dict(second, id=ids[i] + "_case_2"),
                ],
            }
        )
    content["readiness"] = {
        "rule_version": 1,
        "threshold": 80,
        "max_rounds": 2,
        "objectives": objectives,
    }
    return content


def validate_readiness(content, source_sections=None):
    spec = content.get("readiness")
    if spec is None:
        return
    if (
        not isinstance(spec, dict)
        or type(spec.get("rule_version")) is not int
        or spec.get("rule_version") != 1
    ):
        raise ValueError("Unsupported readiness rules")
    if type(spec.get("threshold")) is not int or not 1 <= spec["threshold"] <= 100:
        raise ValueError("Invalid readiness threshold")
    if type(spec.get("max_rounds")) is not int or not 1 <= spec["max_rounds"] <= 2:
        raise ValueError("Allow one or two remediation rounds")
    objectives = spec.get("objectives")
    if not isinstance(objectives, list) or not 1 <= len(objectives) <= 8:
        raise ValueError("Provide one to eight objectives")
    objective_ids, activity_ids, prompts = set(), set(), set()
    for obj in objectives:
        if not isinstance(obj, dict):
            raise ValueError("Invalid objective")
        for key in ("id", "title", "lesson"):
            if not isinstance(obj.get(key), str) or not obj[key].strip():
                raise ValueError("Objectives need an ID, title and lesson")
        if obj["id"] in objective_ids or type(obj.get("critical")) is not bool:
            raise ValueError(
                "Objective IDs must be unique and critical must be boolean"
            )
        objective_ids.add(obj["id"])
        section = obj.get("source_section")
        if (
            type(section) is not int
            or section < 1
            or (source_sections is not None and section > source_sections)
        ):
            raise ValueError("Invalid objective source reference")
        bank = obj.get("reassessments")
        if not isinstance(bank, list) or not 2 <= len(bank) <= 4:
            raise ValueError(
                "Provide two to four fresh reassessment cases per objective"
            )
        for question in [obj.get("diagnostic"), *bank]:
            if not isinstance(question, dict):
                raise ValueError("Invalid activity")
            for key in ("id", "prompt", "explanation"):
                if not isinstance(question.get(key), str) or not question[key].strip():
                    raise ValueError("Activity fields cannot be empty")
            if (
                question["id"] in activity_ids
                or question["prompt"].strip().casefold() in prompts
            ):
                raise ValueError(
                    "Activities must have unique IDs and different prompts"
                )
            activity_ids.add(question["id"])
            prompts.add(question["prompt"].strip().casefold())
            options = question.get("options")
            if (
                not isinstance(options, list)
                or not 2 <= len(options) <= 5
                or any(not isinstance(x, str) or not x.strip() for x in options)
            ):
                raise ValueError("Invalid activity options")
            if type(question.get("answer")) is not int or not 0 <= question[
                "answer"
            ] < len(options):
                raise ValueError("Invalid activity answer")
    reserved = {
        o["id"] + "_lesson_" + str(i)
        for o in objectives
        for i in range(spec["max_rounds"])
    }
    if reserved & activity_ids:
        raise ValueError("Activity IDs cannot use reserved lesson IDs")


def seed_pilot(c):
    from src.workflows.chain import build_course
    from src.workflows.sample_course import add_banks

    title = "Expense procedure readiness — fictional pilot"
    if c.execute("SELECT 1 FROM courses WHERE title=?", (title,)).fetchone():
        return
    rows = c.execute(
        "SELECT c.*,d.body FROM courses c JOIN documents d ON d.id=c.document_id "
        "WHERE d.title=? AND d.approved=1 AND c.status='published' ORDER BY c.id",
        ("Example expense policy v1 — fictional demo",),
    ).fetchall()
    if not rows:
        return
    canonical = [
        "Every reimbursement claim must include an itemized receipt. If a receipt is missing, request a duplicate from the supplier before submitting the claim. A bank statement alone is not sufficient.",
        "Submit expense claims within 30 calendar days of the purchase date. Late claims require manager review and are not automatically accepted.",
        "Expenses above SGD 200 require written manager approval before purchase. Attach that approval to the claim.",
        "Finance reviews complete claims within five business days. If information is missing, Finance returns the claim for correction. Do not submit the same expense twice.",
    ]
    for row in rows:
        expected = add_banks(
            build_course("Expense reimbursement essentials", row["body"])
        )
        if [lesson["text"] for lesson in expected["lessons"]] != canonical:
            continue
        if json.loads(row["content"]) != expected:
            continue  # Do not automatically extend a trainer-modified course.
        content = pilot_content(expected)
        validate_readiness(content, 4)
        c.execute(
            "INSERT INTO courses(title,document_id,content,status) VALUES(?,?,?,'published')",
            (title, row["document_id"], json.dumps(content)),
        )
        break
