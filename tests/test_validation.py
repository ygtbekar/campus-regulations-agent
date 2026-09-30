"""Unit tests for the guardrails. No model calls: these run offline in under a second.

    python -m unittest discover tests
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools
from agent import parse_final_answer

RETRIEVED = {21, 22, 31}  # pretend the search returned these articles in this conversation


def reply(answer: str, sources: list[str]) -> str:
    return json.dumps({"answer": answer, "sources": sources}, ensure_ascii=False)


class FinalAnswerValidation(unittest.TestCase):
    def test_accepts_a_clean_answer_citing_a_retrieved_article(self):
        result = parse_final_answer(reply("Onuncu haftada çekilebilirsin.", ["MADDE 22"]), RETRIEVED)
        self.assertEqual(result.sources, ["MADDE 22"])

    def test_rejects_a_citation_that_was_never_retrieved(self):
        """The most dangerous failure: an invented source looks more trustworthy than a plain guess."""
        with self.assertRaises(ValueError):
            parse_final_answer(reply("Yaz okulunda 3 ders alabilirsin.", ["MADDE 99"]), RETRIEVED)

    def test_rejects_characters_from_another_script(self):
        with self.assertRaises(ValueError):
            parse_final_answer(reply("Mevcut 규lamada bilgi bulamadım.", []), RETRIEVED)

    def test_rejects_a_malformed_source_string(self):
        with self.assertRaises(ValueError):
            parse_final_answer(reply("Bir cevap.", ["yönetmelik madde 22"]), RETRIEVED)

    def test_accepts_harmless_formatting_differences(self):
        """A validator should block real problems, not punish case or code fences."""
        lower_case = parse_final_answer(reply("Ortalama en az 2,00.", ["Madde 31"]), RETRIEVED)
        self.assertEqual(lower_case.sources, ["MADDE 31"])

        fenced = parse_final_answer(
            "```json\n" + reply("Tarihler akademik takvimde.", ["MADDE 21"]) + "\n```", RETRIEVED
        )
        self.assertEqual(fenced.sources, ["MADDE 21"])

    def test_accepts_an_answer_with_no_sources(self):
        result = parse_final_answer(reply("Bunu yönetmelikte bulamadım.", []), RETRIEVED)
        self.assertEqual(result.sources, [])


class Tools(unittest.TestCase):
    def test_gpa_matches_a_hand_calculation(self):
        # (3x4.00 + 4x2.50 + 3x1.00) / 10 = 2.50
        result = tools.calculate_gpa([
            {"credits": 3, "grade": "AA"}, {"credits": 4, "grade": "CB"}, {"credits": 3, "grade": "DD"},
        ])
        self.assertEqual(result["gpa"], 2.5)
        self.assertEqual(result["total_credits"], 10.0)

    def test_grade_table_matches_article_24(self):
        expected = {"AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, "CC": 2.0,
                    "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0, "NA": 0.0}
        self.assertEqual(tools.GRADE_POINTS, expected)

    def test_tools_return_errors_as_data_so_the_model_can_recover(self):
        self.assertIn("error", tools.calculate_gpa([{"credits": 3, "grade": "A+"}]))
        self.assertIn("error", tools.days_until("02.10.2026"))  # wrong date format
        self.assertIn("error", tools.calculate_gpa([]))  # zero credits

    def test_every_tool_schema_has_an_implementation(self):
        names = {schema["function"]["name"] for schema in tools.TOOL_SCHEMAS}
        self.assertEqual(names, set(tools.TOOL_FUNCTIONS))


if __name__ == "__main__":
    unittest.main()
