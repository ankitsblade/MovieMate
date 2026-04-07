import unittest
from unittest.mock import patch

from app.evals.judge import TurnJudgeResult
from app.evals.service import evaluate_retrieval, evaluate_turn


SAMPLE_MOVIE = {
    "primary_title": "No Time to Die",
    "title_type": "movie",
    "start_year": 2021,
    "runtime_minutes": 163,
    "genres": "Action,Thriller",
    "average_rating": 7.3,
    "num_votes": 450000,
    "people_summary": "Daniel Craig, Ana de Armas, Cary Joji Fukunaga",
    "content": "James Bond action thriller featuring Ana de Armas.",
}

SECOND_SAMPLE_MOVIE = {
    "primary_title": "Blade Runner 2049",
    "title_type": "movie",
    "start_year": 2017,
    "runtime_minutes": 164,
    "genres": "Sci-Fi,Drama",
    "average_rating": 8.0,
    "num_votes": 650000,
    "people_summary": "Ryan Gosling, Ana de Armas, Denis Villeneuve",
    "content": "Sci-fi drama featuring Ana de Armas in a supporting role.",
}


class EvalTests(unittest.TestCase):
    def test_retrieval_eval_detects_person_alignment(self):
        result = evaluate_retrieval(
            user_message="movies featuring Ana de Armas",
            intent="movie_query",
            filters={"person_name": "Ana de Armas", "genre": None, "min_year": None, "max_year": None, "max_runtime": None, "min_rating": None},
            results=[SAMPLE_MOVIE],
        )

        self.assertIsNotNone(result)
        self.assertGreater(result["score"], 0.7)

    @patch("app.evals.service.judge_turn")
    def test_turn_eval_includes_llm_scores(self, mock_judge):
        mock_judge.return_value = TurnJudgeResult(
            retrieval_relevance=5,
            evidence_alignment=4,
            groundedness=5,
            helpfulness=4,
            presentation_discipline=4,
            note="Grounded and useful.",
        )

        signal = evaluate_turn(
            user_message="movies featuring Ana de Armas",
            intent="movie_query",
            answer="Here are a couple of strong Ana de Armas picks.",
            filters={"person_name": "Ana de Armas", "genre": None, "min_year": None, "max_year": None, "max_runtime": None, "min_rating": None},
            reranked_movies=[SAMPLE_MOVIE],
            memory_context="",
            show_movie_cards=True,
            latency_ms=880,
        )

        self.assertGreater(signal["overall_score"], 0.7)
        self.assertEqual(signal["details"]["llm_judge"]["groundedness"], 5)
        self.assertEqual(signal["details"]["llm_judge"]["retrieval_relevance"], 5)
        self.assertEqual(len(signal["signals"]), 3)

    @patch("app.evals.service.judge_turn")
    def test_card_mode_eval_keeps_full_result_count(self, mock_judge):
        mock_judge.return_value = TurnJudgeResult(
            retrieval_relevance=4,
            evidence_alignment=4,
            groundedness=4,
            helpfulness=4,
            presentation_discipline=5,
            note="Grounded summary matches the retrieved set.",
        )

        signal = evaluate_turn(
            user_message="feel-good movies under two hours",
            intent="movie_query",
            answer="I found 2 retrieved options that fit your request.\n\nThe cards below are the grounded matches from the retrieved set.",
            filters={"person_name": None, "genre": None, "min_year": None, "max_year": None, "max_runtime": 120, "min_rating": None},
            reranked_movies=[SAMPLE_MOVIE, SECOND_SAMPLE_MOVIE],
            memory_context="",
            show_movie_cards=True,
            latency_ms=1200,
        )

        self.assertEqual(signal["details"]["result_count"], 2)
        self.assertGreater(signal["overall_score"], 0.6)


if __name__ == "__main__":
    unittest.main()
