import unittest
from unittest.mock import MagicMock, patch

from app.graph.router import RouteDecision, classify_intent


class RouterTests(unittest.TestCase):
    @patch("app.graph.router.router_llm")
    def test_classify_intent_prefers_llm_result(self, mock_router):
        mock_router.invoke.return_value = RouteDecision(intent="movie_query", clarify_prompt=None)

        intent, clarify_prompt = classify_intent("hello", [])

        self.assertEqual(intent, "movie_query")
        self.assertIsNone(clarify_prompt)

    @patch("app.graph.router.router_llm", new_callable=MagicMock)
    def test_classify_intent_falls_back_to_heuristics(self, mock_router):
        mock_router.invoke.side_effect = RuntimeError("router failed")
        intent, clarify_prompt = classify_intent("movies with Chris", [])

        self.assertEqual(intent, "clarify")
        self.assertIn("Which Chris do you mean?", clarify_prompt)


if __name__ == "__main__":
    unittest.main()
