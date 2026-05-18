import json
import unittest

from minchoagnt.review import MemoryAddition, ReviewPlan, ReviewPlanValidationError


class ReviewPlanSchemaTests(unittest.TestCase):
    def test_parses_korean_memory_json_and_round_trips(self):
        raw = json.dumps(
            {
                "memory_additions": [
                    {
                        "target": "user",
                        "content": "사용자는 한국어 요약을 선호한다.",
                        "evidence": "기억해줘: 나는 한국어 요약을 선호해",
                    }
                ],
                "skill_creations": [],
            },
            ensure_ascii=False,
        )

        plan = ReviewPlan.from_json(raw)

        self.assertEqual(len(plan.memory_additions), 1)
        self.assertEqual(plan.memory_additions[0].target, "user")
        self.assertEqual(plan.memory_additions[0].content, "사용자는 한국어 요약을 선호한다.")
        self.assertEqual(
            plan.memory_additions[0].evidence,
            "기억해줘: 나는 한국어 요약을 선호해",
        )
        self.assertEqual(ReviewPlan.from_json(plan.to_json()), plan)

    def test_parses_skill_json_with_evidence(self):
        plan = ReviewPlan.from_dict(
            {
                "memory_additions": [],
                "skill_creations": [
                    {
                        "name": "release-checklist",
                        "content": "# Release Checklist\n\n1. Run tests.",
                        "category": "learned",
                        "evidence": "릴리즈할 때 테스트 돌리고 git 상태 확인하는 절차",
                    }
                ],
            }
        )

        self.assertEqual(len(plan.skill_creations), 1)
        self.assertEqual(plan.skill_creations[0].name, "release-checklist")
        self.assertEqual(plan.skill_creations[0].category, "learned")
        self.assertIn("Run tests", plan.skill_creations[0].content)

    def test_rejects_invalid_memory_target(self):
        with self.assertRaisesRegex(ReviewPlanValidationError, "target"):
            ReviewPlan.from_dict(
                {
                    "memory_additions": [
                        {"target": "profile", "content": "bad target"},
                    ],
                    "skill_creations": [],
                }
            )

    def test_rejects_non_string_memory_target_from_direct_constructor(self):
        with self.assertRaisesRegex(ReviewPlanValidationError, "memory target"):
            MemoryAddition(target=123, content="valid content")

    def test_rejects_empty_content(self):
        with self.assertRaisesRegex(ReviewPlanValidationError, "content"):
            ReviewPlan.from_dict(
                {
                    "memory_additions": [
                        {"target": "user", "content": "   "},
                    ],
                    "skill_creations": [],
                }
            )

    def test_rejects_unsafe_skill_name(self):
        with self.assertRaisesRegex(ReviewPlanValidationError, "skill name"):
            ReviewPlan.from_dict(
                {
                    "memory_additions": [],
                    "skill_creations": [
                        {
                            "name": "../release",
                            "content": "# Release\n\n1. Run tests.",
                        }
                    ],
                }
            )

    def test_rejects_malformed_json(self):
        with self.assertRaisesRegex(ReviewPlanValidationError, "JSON"):
            ReviewPlan.from_json("not json")


if __name__ == "__main__":
    unittest.main()
