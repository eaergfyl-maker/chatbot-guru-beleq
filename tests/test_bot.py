"""Scripted conversations against the real graph. Run: python -m unittest discover tests -v"""
import os
import tempfile
import unittest
from datetime import datetime
from unittest import mock

os.environ["PROFILES_FILE"] = os.path.join(tempfile.mkdtemp(), "profiles.json")

from src import nlp, persona, profiles, search  # noqa: E402
from src.graph import ask, build_graph, start, state_of  # noqa: E402
from src.knowledge import validate  # noqa: E402


class Chat(unittest.TestCase):
    def setUp(self):
        self.graph = build_graph()
        self.tid = self.id()

    def say(self, text):
        return ask(self.graph, text, self.tid)

    def begin(self, name="Budi"):
        start(self.graph, self.tid)
        return self.say(name)


class Knowledge(unittest.TestCase):
    def test_kb_is_valid(self):
        self.assertEqual(validate(), [])


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
        self.assertEqual(state_of(self.graph, self.tid)["user_name"], "Budi")


class Understanding(Chat):
    def test_invalid_input(self):
        self.begin()
        for bad in ("?????", "   ", "x" * 600):
            self.assertIn("rephrase" if bad == "?????" else "", self.say(bad))
        self.assertEqual(state_of(self.graph, self.tid)["stage"], "menu")

    def test_typo_and_synonym_answers(self):
        self.begin()
        reply = self.say("what is the gendnag belek?")
        self.assertIn("I read that as", reply)
        self.assertIn("Sasak", reply)
        self.assertIn("big", self.say("what does beleq mean?"))
        self.assertIn("war", self.say("tell me about the origin of the big drum ensemble"))

    def test_offtopic_and_unknown(self):
        self.begin()
        self.assertIn("outside what I teach", self.say("What is the capital of France?"))

    def test_followup_uses_previous_question(self):
        self.begin()
        self.say("what instruments are used?")
        self.assertIn("mama", self.say("tell me more about the drums"))

    def test_spelling_does_not_mangle_normal_words(self):
        self.assertEqual(nlp.correct_spelling("how long did the players stand there"), "how long did the players stand there")

    def test_menu_number_and_words(self):
        self.begin()
        self.assertIn("Ask away", self.say("2"))
        self.assertIn("Report card", self.say("show my progress"))
        self.assertIn("Report card", self.say("5"))


class Teaching(Chat):
    def test_lesson_flow_with_hint_and_completion(self):
        self.begin()
        self.assertIn("Lesson 1", self.say("1"))
        wrong = self.say("pizza")
        self.assertIn("clue", wrong)
        self.assertIn("Step 2 of 2", self.say("the Sasak people on Lombok"))
        self.assertIn("Lesson complete", self.say("it is a percussion group"))
        self.assertEqual(state_of(self.graph, self.tid)["progress"]["lessons_done"], ["overview"])
        self.assertEqual(profiles.load("Budi")["lessons_done"], ["overview"])

    def test_lesson_topic_selection_and_question_inside_lesson(self):
        self.begin()
        self.assertIn("The instruments", self.say("teach me about the instruments"))
        reply = self.say("what does beleq mean?")
        self.assertIn("big", reply)
        self.assertIn("back to our lesson", reply)
        self.assertEqual(state_of(self.graph, self.tid)["stage"], "lesson")
        self.assertIn("Step 2 of 2", self.say("gendang mama and gendang nina"))

    def test_skip_reveals_answer(self):
        self.begin()
        self.say("lesson")
        self.assertIn("let's learn it together", self.say("i don't know"))

    def test_leave_lesson(self):
        self.begin()
        self.say("lesson")
        self.assertIn("1. Start a lesson", self.say("stop"))
        self.assertEqual(state_of(self.graph, self.tid)["stage"], "menu")

    def test_quiz_runs_to_summary(self):
        self.begin()
        self.assertIn("Question 1", self.say("quiz me"))
        for _ in range(12):
            reply = self.say("skip")
            if "Quiz finished" in reply:
                break
        self.assertIn("Quiz finished", reply)
        self.assertEqual(state_of(self.graph, self.tid)["stage"], "menu")
        self.assertEqual(state_of(self.graph, self.tid)["progress"]["quiz_total"], 5)

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


class Search(unittest.TestCase):
    def test_unrelated_query_has_no_hits(self):
        self.assertEqual(search.search("capital of France"), [])


if __name__ == "__main__":
    unittest.main()
