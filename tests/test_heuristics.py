import unittest

from app.rules.heuristics import (
    answer_looks_complete,
    build_card_mode_answer,
    extract_person_name,
    infer_clarify_prompt,
    is_memory_lookup_message,
    is_recent_clarify_prompt,
    is_short_followup_message,
    looks_like_clarify_response,
    person_name_matches_text,
    replace_single_name_query,
    sanitize_answer,
    should_show_movie_cards,
    should_use_memory,
)


class HeuristicsTests(unittest.TestCase):
    def test_extract_person_name_from_full_query(self):
        self.assertEqual(
            extract_person_name("movies featuring Ana de Armas"),
            "Ana de Armas",
        )

    def test_extract_person_name_from_bare_name(self):
        self.assertEqual(
            extract_person_name("ana de armas"),
            "Ana de Armas",
        )

    def test_reject_visual_phrase_as_person_name(self):
        self.assertIsNone(extract_person_name("movies with strong visuals"))

    def test_clarify_prompt_for_single_name(self):
        prompt = infer_clarify_prompt("movies with Chris", has_prior_context=False)
        self.assertIn("Which Chris do you mean?", prompt)

    def test_clarify_prompt_for_generic_recommendation(self):
        prompt = infer_clarify_prompt("recommend something", has_prior_context=False)
        self.assertIn("What kind of movie", prompt)

    def test_memory_lookup_detection(self):
        self.assertTrue(is_memory_lookup_message("Do you remember my name?"))

    def test_short_followup_detection(self):
        self.assertTrue(is_short_followup_message("newer ones"))
        self.assertFalse(is_short_followup_message("recommend dark thrillers"))

    def test_clarify_response_detection(self):
        self.assertTrue(looks_like_clarify_response("Ana de armas"))
        self.assertTrue(
            is_recent_clarify_prompt(
                "Which Ana do you mean? If you can, give me the full name of the actor or director."
            )
        )

    def test_replace_single_name_query(self):
        self.assertEqual(
            replace_single_name_query("Movies with ana", "Ana de Armas"),
            "Movies with Ana de Armas",
        )

    def test_card_rendering_rules(self):
        self.assertTrue(should_show_movie_cards("give me a list of space movies", "movie_query", True))
        self.assertFalse(should_show_movie_cards("who directed Arrival?", "movie_query", True))

    def test_memory_usage_rules(self):
        self.assertTrue(should_use_memory("recommend something for me", "movie_query"))
        self.assertFalse(should_use_memory("who directed Arrival?", "movie_query"))

    def test_sanitize_answer_removes_card_section(self):
        answer = "Here are some picks.\n\nCards:\n- No Time to Die\n- Blade Runner 2049"
        self.assertEqual(sanitize_answer(answer, True), "Here are some picks.")

    def test_card_mode_answer_does_not_list_titles(self):
        results = [
            {
                "primary_title": "Kung Fu Panda",
                "runtime_minutes": 92,
                "start_year": 2008,
                "genres": "Animation,Comedy",
            },
            {
                "primary_title": "Happy",
                "runtime_minutes": 76,
                "start_year": 2012,
                "genres": "Documentary",
            },
        ]

        answer = build_card_mode_answer("feel-good movies under two hours", results)

        self.assertIn("feel-good mood", answer)
        self.assertIn("You’ll find 2 options below.", answer)
        self.assertNotIn("Kung Fu Panda", answer)
        self.assertNotIn("Happy", answer)
        self.assertNotIn("retrieved set", answer)
        self.assertTrue(answer_looks_complete(answer))

    def test_detect_incomplete_answer(self):
        self.assertFalse(answer_looks_complete("This charming documentary follows"))
        self.assertTrue(answer_looks_complete("This charming documentary follows a playful family."))

    def test_person_name_matching_uses_word_boundaries(self):
        self.assertTrue(
            person_name_matches_text("Ana de Armas", "Cast: Ana de Armas, Daniel Craig"),
        )
        self.assertFalse(
            person_name_matches_text("Ana de Armas", "A documentary about Panama and arms trafficking"),
        )


if __name__ == "__main__":
    unittest.main()
