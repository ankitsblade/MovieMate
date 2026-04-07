import unittest
from unittest.mock import patch

from app.graph.nodes import retrieve_node


class NodeTests(unittest.TestCase):
    @patch("app.graph.nodes.search_movies")
    @patch("app.graph.nodes.get_query_embedding")
    @patch("app.graph.nodes.extract_filters")
    def test_retrieve_node_preserves_person_filter_from_user_message(self, mock_extract_filters, mock_embedding, mock_search):
        mock_embedding.return_value = [0.0] * 384
        mock_search.return_value = []
        mock_extract_filters.side_effect = [
            {
                "min_year": None,
                "max_year": None,
                "max_runtime": None,
                "min_rating": None,
                "genre": None,
                "person_name": None,
            },
            {
                "min_year": None,
                "max_year": None,
                "max_runtime": None,
                "min_rating": None,
                "genre": None,
                "person_name": "Ana de Armas",
            },
        ]

        state = {
            "needs_retrieval": True,
            "user_message": "Ana de Armas",
            "rewritten_query": "feel-good movies under 2 hours",
        }

        result = retrieve_node(state)

        self.assertEqual(result["filters"]["person_name"], "Ana de Armas")
        self.assertEqual(mock_search.call_args.kwargs["person_name"], "Ana de Armas")


if __name__ == "__main__":
    unittest.main()
