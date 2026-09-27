"""Typed actions advertised to the model and checked before tool execution."""

import json
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, TypeAdapter

FORMAT_REPAIR_PROMPT = (
    "Your previous response was not valid JSON and was not executed. "
    "Return exactly one JSON object matching the original response contract: "
    '{"tool":"allowed_tool","args":{...}} or, only when allowed, '
    '{"answer":"concise answer"}. No introduction, explanation, or Markdown outside '
    "the object. Use only the supplied tools and evidence; do not invent values."
)


class StrictObject(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmptyArgs(StrictObject):
    pass


class SearchArgs(StrictObject):
    query: str = Field(min_length=1, max_length=2000, pattern=r"\S")


class CourseArgs(StrictObject):
    course_id: StrictInt = Field(gt=0)


class LessonArgs(CourseArgs):
    skill: StrictInt = Field(ge=0)


class ActivityArgs(StrictObject):
    session_id: StrictInt = Field(gt=0)
    activity_id: str = Field(min_length=1, max_length=200)


TOOL_REGISTRY = {
    "get_learning_state": (
        "Read your saved readiness sessions, critical gaps and eligible activities.",
        EmptyArgs,
    ),
    "select_approved_activity": (
        "Recommend one activity from the session's eligible_actions. Does not submit answers or change scores.",
        ActivityArgs,
    ),
    "get_my_progress": (
        "Read the signed-in learner's courses and recent results.",
        EmptyArgs,
    ),
    "retrieve_sources": ("Search approved policy passages for evidence.", SearchArgs),
    "get_course_outline": (
        "List an approved course's lesson titles and skill indices, without answer keys.",
        CourseArgs,
    ),
    "recommend_lesson": (
        "Read an approved lesson for a course and zero-based skill index.",
        LessonArgs,
    ),
}


class ToolDecision(StrictObject):
    tool: Literal[
        "get_my_progress",
        "retrieve_sources",
        "get_course_outline",
        "recommend_lesson",
        "get_learning_state",
        "select_approved_activity",
    ]
    args: dict


class FinalDecision(StrictObject):
    answer: str = Field(min_length=1, max_length=16000, pattern=r"\S")


DECISION = TypeAdapter(ToolDecision | FinalDecision)


def parse_decision(text):
    if not isinstance(text, str) or len(text) > 20000:
        raise ValueError("Response must be a JSON object under 20,000 characters")
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return DECISION.validate_python(json.loads(clean))


def validate_tool(name, args):
    if not isinstance(name, str) or name not in TOOL_REGISTRY:
        raise ValueError("Tool is not allowed")
    return TOOL_REGISTRY[name][1].model_validate(args).model_dump()


def tool_catalog():
    return [
        {
            "name": name,
            "description": description,
            "parameters": schema.model_json_schema(),
        }
        for name, (description, schema) in TOOL_REGISTRY.items()
    ]
