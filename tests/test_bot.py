"""Scripted conversations against the real graph. Run: python -m unittest discover tests -v"""
import os
import tempfile
import unittest
from datetime import datetime
from unittest import mock

_tmp = tempfile.mkdtemp()
os.environ["PROFILES_FILE"] = os.path.join(_tmp, "profiles.json")
os.environ["CUQ_FILE"] = os.path.join(_tmp, "cuq.csv")

from eval import cuq  # noqa: E402
from src import nlp, persona, profiles, search  # noqa: E402
from src.graph import ask, build_graph, start, state_of  # noqa: E402
from src.knowledge import get_topic, glossary, references, topics, validate  # noqa: E402
from src.semantic_net import load_edges  # noqa: E402


class Chat(unittest.TestCase):
    def setUp(self):
        if os.path.exists(os.environ["PROFILES_FILE"]):
            os.remove(os.environ["PROFILES_FILE"])  # each test starts with a new learner
        self.graph = build_graph()
        self.tid = self.id()

    def say(self, text):
        return ask(self.graph, text, self.tid)

    def begin(self, name="Budi"):
        start(self.graph, self.tid)
        return self.say(name)

    def state(self):
        return state_of(self.graph, self.tid)


class Knowledge(unittest.TestCase):
    def test_kb_is_valid(self):
        self.assertEqual(validate(), [])

    def test_every_fact_and_edge_is_cited(self):
        refs = references()
        for t in topics():
            for fact in t["facts"]:
                self.assertTrue(fact["sources"], fact["text"])
        for term, entry in glossary().items():
            self.assertTrue(entry["sources"], term)
        for e in load_edges():
            self.assertTrue(all(k in refs for k in e["sources"]), e)

    def test_every_reference_has_a_notes_file(self):
        folder = os.path.join(os.path.dirname(__file__), "..", "data", "sources")
        for key in references():
            self.assertTrue(os.path.exists(os.path.join(folder, f"{key}.md")), key)

    def test_every_lesson_answer_is_accepted_by_its_own_explanation(self):
        for t in topics():
            for step in t["lesson"]:
                hit = sum(nlp.concept_hit(step["explain"], g) for g in step["answer"])
                self.assertGreater(hit, 0, step["question"])


class Opening(Chat):
    def test_time_greeting(self):
        for hour, word in ((9, "Good morning"), (14, "Good afternoon"), (20, "Good evening")):
            with mock.patch.object(persona, "now", return_value=datetime(2026, 1, 1, hour)):
                self.assertTrue(start(build_graph(), f"t{hour}").startswith(word))

    def test_bot_speaks_first_and_asks_name(self):
        text = start(self.graph, self.tid)
        self.assertIn("Guru Beleq", text)
        self.assertIn("what should I call you", text)

    def test_name_capture_and_menu(self):
        start(self.graph, self.tid)
        self.assertIn("didn't catch your name", self.say("what is going on here today friends?"))
        reply = self.say("my name is budi")
        self.assertIn("Nice to meet you, Budi", reply)
        self.assertIn("1. Start a lesson", reply)
        self.assertEqual(self.state()["user_name"], "Budi")

    def test_name_extraction(self):
        for text, name in (("Budi", "Budi"), ("I'm Sari", "Sari"), ("hello, my name is ana", "Ana"), ("José", "José"),
                           ("Anne-Marie", "Anne-Marie"), ("call me O'Brien", "O'Brien"), ("Budi Santoso", "Budi")):
            self.assertEqual(persona.extract_name(text), name, text)
        for text in ("good morning", "hello", "I'm fine", "what is this", "him and her and them"):
            self.assertIsNone(persona.extract_name(text), text)


class Understanding(Chat):
    def test_invalid_input(self):
        self.begin()
        self.assertIn("rephrase", self.say("?????"))
        self.assertIn("didn't catch anything", self.say("   "))
        self.assertIn("a bit long", self.say("x y " * 300))
        self.assertEqual(self.state()["stage"], "menu")

    def test_answers_carry_harvard_citations(self):
        self.begin()
        reply = self.say("what does beleq mean?")
        self.assertIn("big", reply)
        self.assertIn("(Saputra, 2019", reply)

    def test_typo_and_synonym_answers(self):
        self.begin()
        reply = self.say("what is the gendnag belek?")
        self.assertIn("I read that as", reply)
        self.assertIn("Sasak", reply)
        origin_reply = self.say("tell me about the origin of the big drum ensemble")
        self.assertIn("war", origin_reply)
        self.assertNotIn("don't have an exact answer", origin_reply)

    def test_corrected_facts(self):
        self.begin()
        self.assertIn("tempo", self.say("what does the petuq do?"))
        self.assertIn("petuq", self.say("what is an oncer?"))
        self.assertIn("mame", self.say("what are the two drums called?"))

    def test_uncertain_history_is_not_stated_as_fact(self):
        self.begin()
        self.assertIn("uncertain", self.say("who invented the gendang beleq?"))

    def test_partial_match_is_admitted(self):
        self.begin()
        self.assertIn("don't have an exact answer", self.say("what colour is the van of the ensemble?"))

    def test_question_types_get_the_right_answer(self):
        for question, expected in (
            ("how many players are there?", "dozen"),
            ("when is it played?", "wedding"),
            ("how long are the drums?", "94 cm"),
            ("where can i see it?", "Sade"),
            ("is it dying out?", "kecimol"),
            ("how do you play the drums?", "mallet"),
            ("what do they wear?", "batik"),
            ("what are the instruments?", "reyong"),
            ("who plays it?", "Sasak musicians"),
            ("what is it made of?", "wood"),
            ("what does a gong do?", "closes"),
            ("what is the meaning of the gendang beleq?", "big drum"),
            ("where does it come from?", "Lombok"),
            ("tell me about nyongkolan", "procession"),
        ):
            self.tid = question
            self.begin()
            self.assertIn(expected, self.say(question), question)

    def test_spelling_leaves_look_alone(self):
        self.assertEqual(nlp.correct_spelling("what does it look like"), "what does it look like")

    def test_offtopic_and_unknown(self):
        self.begin()
        self.assertIn("outside what I teach", self.say("What is the capital of France?"))
        self.assertIn("outside what I teach", self.say("Who invented the guitar?"))

    def test_tell_me_more_gives_new_facts(self):
        self.begin()
        first = self.say("what instruments are used?")
        self.assertNotEqual(first, self.say("tell me more about the instruments"))

    def test_spelling_does_not_mangle_normal_words(self):
        text = "how long did the players stand there"
        self.assertEqual(nlp.correct_spelling(text), text)
        self.assertEqual(nlp.correct_spelling("Lombock"), "Lombok")

    def test_menu_numbers_and_words(self):
        self.begin()
        self.assertIn("Ask away", self.say("2"))
        self.assertIn("Report card", self.say("show my progress"))
        self.assertIn("Report card", self.say("5"))
        self.assertIn("Saputra, G.A.M.", self.say("7"))
        self.assertIn("Sasak and musical glossary", self.say("8"))
        self.assertIn("nyongkolan", self.say("show me the glossary"))
        self.assertIn("isn't on the menu", self.say("9"))

    def test_identity_and_decline(self):
        self.begin()
        self.assertIn("Guru Beleq", self.say("who are you?"))
        self.assertIn("That's fine", self.say("no"))

    def test_question_about_learning_is_not_a_lesson_request(self):
        self.begin()
        self.say("how do the players learn the drums?")
        self.assertEqual(self.state()["stage"], "menu")


class Teaching(Chat):
    def test_lesson_flow_with_hint_and_completion(self):
        self.begin()
        self.assertIn("Lesson 1", self.say("1"))
        self.assertIn("clue", self.say("pizza"))
        self.assertIn("Step 2 of 2", self.say("the Sasak people on Lombok"))
        reply = self.say("it is a percussion group")
        self.assertIn("Lesson complete", reply)
        self.assertIn("Saputra, 2019", reply)
        self.assertEqual(self.state()["progress"]["lessons_done"], ["overview"])
        self.assertEqual(profiles.load("Budi")["lessons_done"], ["overview"])

    def test_next_continues_with_the_next_lesson(self):
        self.begin()
        self.say("lesson")
        self.say("sasak lombok")
        self.say("percussion")
        self.assertIn("What does the name mean?", self.say("next"))

    def test_lesson_topic_selection_and_question_inside_lesson(self):
        self.begin()
        self.assertIn("The instruments", self.say("teach me about the instruments"))
        reply = self.say("what does beleq mean?")
        self.assertIn("big", reply)
        self.assertIn("back to our lesson", reply)
        self.assertEqual(self.state()["stage"], "lesson")
        self.assertIn("Step 2 of 2", self.say("gendang mame and gendang nine"))

    def test_both_drum_spellings_are_accepted(self):
        self.begin()
        self.say("teach me about the instruments")
        self.assertIn("Step 2 of 2", self.say("mama and nina"))

    def test_answer_phrased_as_a_question_counts(self):
        self.begin()
        self.say("teach me about weddings")
        self.assertIn("Step 2 of 2", self.say("is it a wedding?"))

    def test_hint_keeps_the_attempt(self):
        self.begin()
        self.say("lesson")
        self.assertIn("clue", self.say("hint"))
        self.assertEqual(self.state()["lesson"]["attempts"], 0)

    def test_skip_reveals_answer(self):
        self.begin()
        self.say("lesson")
        self.assertIn("let's learn it together", self.say("i don't know"))

    def test_leave_lesson(self):
        self.begin()
        self.say("lesson")
        self.assertIn("1. Start a lesson", self.say("stop"))
        self.assertEqual(self.state()["stage"], "menu")

    def test_quiz_runs_to_summary(self):
        self.begin()
        self.assertIn("Question 1", self.say("quiz me"))
        for _ in range(12):
            reply = self.say("skip")
            if "Quiz finished" in reply:
                break
        self.assertIn("Quiz finished", reply)
        self.assertEqual(self.state()["stage"], "menu")
        self.assertEqual(self.state()["progress"]["quiz_total"], 5)

    def test_quiz_progress_is_saved_when_leaving_early(self):
        self.begin("Dewi")
        self.say("quiz")
        self.say("skip")
        self.say("stop")
        self.assertEqual(profiles.load("Dewi")["quiz_total"], 1)

    def test_recommendation_has_reasons(self):
        self.begin()
        reply = self.say("what should I learn next?")
        self.assertIn("recommend", reply)
        self.assertIn("haven't done this lesson yet", reply)

    def test_struggling_gets_encouragement(self):
        self.begin()
        self.assertIn("go slowly", self.say("I am so confused and it is too hard"))

    def test_returning_learner_is_remembered(self):
        self.begin("Sari")
        self.say("lesson")
        self.say("sasak lombok")
        self.say("percussion")
        self.say("bye")
        start(self.graph, "again")
        self.assertIn("Welcome back, Sari", ask(self.graph, "Sari", "again"))

    def test_goodbye(self):
        self.begin()
        self.assertIn("Goodbye, Budi", self.say("bye"))

    def test_a_failing_node_does_not_crash_the_chat(self):
        self.begin()
        with mock.patch("src.search.search", side_effect=RuntimeError("boom")):
            self.assertIn("something went wrong", self.say("what instruments are used?"))
        with mock.patch("src.search.mentions_domain", side_effect=RuntimeError("boom")):
            self.assertIn("something went wrong", self.say("is that so"))
            self.assertEqual(self.state()["intent"], "error")
        self.assertIn("Report card", self.say("5"))


class Search(unittest.TestCase):
    def test_unrelated_query_has_no_hits(self):
        self.assertEqual(search.search("capital of France"), [])

    def test_short_keyword_needs_a_whole_word(self):
        self.assertFalse(search.keyword_hit("war", "is it warm"))
        self.assertTrue(search.keyword_hit("war", "going to war"))
        self.assertTrue(search.keyword_hit("wedding", "at weddings"))

    def test_topic_keywords_point_to_their_topic(self):
        for query, topic in (("what do players wear", "players"), ("what is nyongkolan", "occasions"),
                             ("which instrument keeps the tempo", "instruments")):
            self.assertIn(search.search(query)[0]["topic"], (topic, "glossary"), query)
            self.assertTrue(get_topic(topic))


class CUQ(unittest.TestCase):
    def test_score_formula(self):
        self.assertEqual(cuq.score([5, 1] * 8), 100)
        self.assertEqual(cuq.score([1, 5] * 8), 0)
        self.assertEqual(cuq.score([3] * 16), 50)
        self.assertEqual(cuq.score([4, 2] * 8), 75)

    def test_invalid_answers_rejected(self):
        for bad in ([3] * 15, [3] * 17, [0] * 16, [6] * 16):
            with self.assertRaises(ValueError):
                cuq.score(bad)

    def test_has_16_items(self):
        self.assertEqual(len(cuq.ITEMS), 16)

    def test_save_and_summarise(self):
        with mock.patch.dict(os.environ, {"CUQ_FILE": os.path.join(_tmp, "cuq_summary.csv")}):
            self.assertIsNone(cuq.summarise(cuq.load()))
            cuq.save([5, 1] * 8, "great, really")
            cuq.save([3] * 16)
            s = cuq.summarise(cuq.load())
        self.assertEqual(s["n"], 2)
        self.assertEqual(s["mean"], 75)
        self.assertEqual(s["items"][0], 4)
        self.assertEqual(s["items"][1], 2)


if __name__ == "__main__":
    unittest.main()
