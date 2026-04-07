import unittest
from unittest.mock import MagicMock, patch

from app.retrieval.query_parser import RetrievalParseResult, extract_filters


class QueryParserTests(unittest.TestCase):
    @patch("app.retrieval.query_parser.retrieval_parser_llm")
    def test_extract_filters_prefers_llm_result(self, mock_parser):
        mock_parser.invoke.return_value = RetrievalParseResult(
            rewritten_query="thrillers with Ana de Armas under 2 hours",
            person_name="Ana de Armas",
            genre="Thriller",
            min_year=None,
            max_year=None,
            max_runtime=120,
            min_rating=None,
        )

        filters = extract_filters("thrillers with Ana de Armas under 2 hours")

        self.assertEqual(filters["person_name"], "Ana de Armas")
        self.assertEqual(filters["genre"], "Thriller")
        self.assertEqual(filters["max_runtime"], 120)

    @patch("app.retrieval.query_parser.retrieval_parser_llm", new_callable=MagicMock)
    def test_extract_filters_falls_back_to_heuristics(self, mock_parser):
        mock_parser.invoke.side_effect = RuntimeError("parser failed")
        filters = extract_filters("movies featuring Ana de Armas under 2 hours")

        self.assertEqual(filters["person_name"], "Ana de Armas")
        self.assertEqual(filters["max_runtime"], 120)


if __name__ == "__main__":
    unittest.main()
