import unittest, tempfile, json
from pathlib import Path
from src.tools import db_queries as core
from src.core.state import snapshot
from src.workflows.router import act


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        core.DB = Path(self.tmp.name) / "test.db"
        core.init()
        self.t = core.user(core.login("trainer", "LearnDemo2026!"))
        self.u = core.user(core.login("learner", "LearnDemo2026!"))
        self.a = core.user(core.login("alex", "LearnDemo2026!"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_auth(self):
        with self.assertRaises(ValueError):
            core.login("trainer", "bad")
        self.assertIsNone(core.user("invalid"))

    def test_permissions(self):
        with self.assertRaises(PermissionError):
            act(self.u, "/api/document", {"title": "x", "body": "a" * 100})

    def test_keys_hidden(self):
        q = snapshot(self.u)["courses"][0]["content"]["questions"][0]
        self.assertNotIn("answer", q)
        self.assertNotIn("explanation", q)

    def test_scoring_and_isolation(self):
        questions = snapshot(self.t)["courses"][0]["content"]["questions"]
        answers = [q["answer"] for q in questions]
        r = act(
            self.u,
            "/api/attempt",
            {"course_id": 1, "phase": "diagnostic", "answers": answers},
        )
        self.assertEqual(r["score"], 100)
        self.assertEqual(r["next_action"], "take_assessment")
        self.assertEqual(len(snapshot(self.a)["attempts"]), 0)
        answers = [
            q["answer"]
            for q in snapshot(self.t)["courses"][0]["content"]["assessment_questions"]
        ]
        r = act(
            self.u,
            "/api/attempt",
            {"course_id": 1, "phase": "assessment", "answers": answers},
        )
        self.assertEqual(r["next_action"], "completed")

    def test_adaptation(self):
        qs = snapshot(self.t)["courses"][0]["content"]["questions"]
        r = act(
            self.u,
            "/api/attempt",
            {
                "course_id": 1,
                "phase": "diagnostic",
                "answers": [(q["answer"] + 1) % 3 for q in qs],
            },
        )
        self.assertEqual(r["score"], 0)
        self.assertEqual(r["next_action"], "review_lessons")

    def test_invalid_attempt(self):
        with self.assertRaises(ValueError):
            act(
                self.u,
                "/api/attempt",
                {"course_id": 1, "phase": "diagnostic", "answers": [True] * 4},
            )
        self.assertEqual(snapshot(self.u)["attempts"], [])

    def test_approval_revocation(self):
        act(self.t, "/api/document/approve", {"id": 1, "approved": False})
        self.assertEqual(snapshot(self.u)["courses"], [])
        with self.assertRaises(ValueError):
            act(
                self.u,
                "/api/attempt",
                {"course_id": 1, "phase": "diagnostic", "answers": [0] * 4},
            )

    def test_draft_publish(self):
        initial_count = len(snapshot(self.u)["courses"])
        act(self.t, "/api/course/create", {"document_id": 1})
        self.assertEqual(len(snapshot(self.u)["courses"]), initial_count)
        draft = snapshot(self.t)["courses"][-1]
        act(
            self.t,
            "/api/course/publish",
            {"id": draft["id"], "content": draft["content"]},
        )
        self.assertEqual(len(snapshot(self.u)["courses"]), initial_count + 1)
        with self.assertRaises(ValueError):
            act(
                self.t,
                "/api/course/publish",
                {"id": draft["id"], "content": draft["content"]},
            )

    def test_unapproved_source(self):
        act(
            self.t,
            "/api/document",
            {
                "title": "Private draft",
                "body": "Never show this unapproved material. " * 4,
            },
        )
        self.assertEqual(len(snapshot(self.u)["documents"]), 1)
        with self.assertRaises(ValueError):
            act(self.t, "/api/course/create", {"document_id": 2})


if __name__ == "__main__":
    unittest.main()
