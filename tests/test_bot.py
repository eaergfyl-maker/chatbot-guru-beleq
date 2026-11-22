"""Scripted conversations against the real graph. Run: python -m unittest discover tests -v"""
import io
import json
import os
import re
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

_tmp = tempfile.mkdtemp()
os.environ["PROFILES_FILE"] = os.path.join(_tmp, "profiles.json")
os.environ["CUQ_FILE"] = os.path.join(_tmp, "cuq.csv")
os.environ["GEMINI_ENABLED"] = "0"  # the tests never call Gemini, even if a local .env has a key; Gemini tests mock it

import server  # noqa: E402
from eval import cuq  # noqa: E402
from src import i18n, llm, nlp, persona, profiles, sandbox, search  # noqa: E402
from src.graph import ask, build_graph, start, state_of, switch_language  # noqa: E402
from src.knowledge import get_topic, glossary, load_translation, references, topics, validate  # noqa: E402
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
        self.begin()
        self.assertIn("Good morning, Budi", self.say("good morning"))
        self.assertIn("Good evening, Budi", self.say("good evening"))
        self.assertIn("Good afternoon, Budi", self.say("good afternoon"))
        self.assertIn("Good morning, Budi", self.say("morning"))
        self.assertIn("Good evening, Budi", self.say("evening"))

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


class SixSeven(Chat):
    def test_during_lesson_returns_to_question_without_using_an_attempt(self):
        self.begin()
        self.say("1")
        before = self.state()["lesson"]
        question = get_topic(before["topic"])["lesson"][before["step"]]["question"]
        reply = self.say("67")
        self.assertTrue(reply.startswith("🤲 67"))
        self.assertIn(f"back to our lesson: {question}", reply)
        self.assertEqual(self.state()["lesson"], before)
        self.assertEqual(self.state()["stage"], "lesson")

    def test_during_quiz_returns_to_question(self):
        self.begin()
        self.say("3")
        before = self.state()["quiz"]
        reply = self.say("67")
        self.assertTrue(reply.startswith("🤲 67"))
        self.assertIn("back to the quiz", reply)
        self.assertEqual(self.state()["quiz"], before)

    def test_at_menu_shows_the_menu(self):
        self.begin()
        reply = self.say("67")
        self.assertTrue(reply.startswith("🤲 67"))
        self.assertIn("Start a lesson", reply)
        self.assertNotIn("isn't on the menu", reply)

    def test_when_asked_for_a_name_still_asks(self):
        start(self.graph, self.tid)
        reply = self.say("67")
        self.assertTrue(reply.startswith("🤲 67"))
        self.assertIn("what should I call you", reply)
        self.assertEqual(self.state()["stage"], "ask_name")

    def test_other_unknown_numbers_still_explained(self):
        self.begin()
        self.assertIn("isn't on the menu", self.say("66"))


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

    def test_read_only_disk_still_returns_score(self):
        with mock.patch.object(cuq, "save", side_effect=OSError("read-only file system")):
            self.assertEqual(server.submit_cuq([3] * 16, ""), {"score": 50.0, "saved": False})


class Hosting(unittest.TestCase):
    def test_vercel_clock_uses_utc_plus_8(self):
        with mock.patch.dict(os.environ, {"VERCEL": "1"}):
            self.assertEqual(persona.now().utcoffset(), timedelta(hours=8))

    def test_local_clock_uses_the_computers_time(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("VERCEL", None)
            self.assertIsNone(persona.now().tzinfo)

    def test_avatar_reactions_match_turn_outcomes(self):
        self.assertEqual(persona.reaction_of({"stage": "ask_name"}, "Good morning!"), "greeting")
        self.assertEqual(persona.reaction_of({"intent": "six_seven"}, "🤲 67"), "six_seven")
        self.assertEqual(persona.reaction_of({"intent": "lesson_reply"}, "Excellent! The Gendang Beleq..."), "celebrate")
        self.assertEqual(persona.reaction_of({"intent": "lesson_reply"}, "Here's a clue: Think of..."), "thinking")
        self.assertEqual(persona.reaction_of({"intent": "offtopic"}, "That's outside what I teach"), "comfort")
        self.assertEqual(persona.reaction_of({"intent": "qa"}, "Gendang means drum."), "teaching")


class SandboxStations(unittest.TestCase):
    def test_every_station_phrase_matches_exactly_one_fact(self):
        for spec in sandbox.STATIONS:
            for topic_id, phrase in spec["facts"]:
                self.assertEqual(len(sandbox.find_facts(topic_id, phrase)), 1, f"{spec['id']}: {phrase!r}")

    def test_payload_has_eight_cited_stations(self):
        d = sandbox.sandbox_payload()
        self.assertEqual(d["total"], 8)
        ids = [s["id"] for s in d["stations"]]
        self.assertEqual(len(set(ids)), 8)
        self.assertIn("guru", ids)
        for s in d["stations"]:
            self.assertTrue(s["facts"], s["id"])
            self.assertTrue(s["references"], s["id"])
            for f in s["facts"] + s["terms"]:
                self.assertRegex(f["cite"], r"^\(.+, (\d{4}|n\.d\.).*\)$")
            self.assertEqual(len(s["terms"]), len(next(x for x in sandbox.STATIONS if x["id"] == s["id"])["terms"]))

    def test_station_facts_come_from_the_knowledge_base(self):
        kb_facts = {f["text"] for t in topics() for f in t["facts"]}
        for s in sandbox.sandbox_payload()["stations"]:
            for f in s["facts"]:
                self.assertIn(f["text"], kb_facts)


class WebRoutes(unittest.TestCase):
    """Starts the real request handler on a free port and requests every page and API route."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read().decode("utf-8", "replace")

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())

    def test_landing_page_offers_both_modes(self):
        status, ctype, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn('href="/chat"', body)
        self.assertIn('href="/sandbox"', body)
        self.assertIn("/avatar.png", body)

    def test_chat_page_keeps_its_features_and_links_home(self):
        for path in ("/chat", "/chat/"):
            status, _, body = self.get(path)
            self.assertEqual(status, 200)
            for feature in ('id="explore"', 'id="export"', 'id="cuq"', 'id="guru-puppet"', 'id="quickbar"', 'href="/"'):
                self.assertIn(feature, body)

    def test_sandbox_page_is_a_self_contained_canvas_game(self):
        status, _, body = self.get("/sandbox")
        self.assertEqual(status, 200)
        self.assertIn('<canvas id="game"', body)
        self.assertIn("/api/sandbox", body)
        self.assertIn('id="rate"', body)
        self.assertIn('href="/"', body)
        # no external scripts or styles; the only script file is the shared language switch from this server
        self.assertEqual(re.findall(r'<script[^>]+src="([^"]+)"', body), ["/lang.js"])
        self.assertNotRegex(body, r'<link[^>]+stylesheet')

    def test_sandbox_api_returns_stations(self):
        status, ctype, body = self.get("/api/sandbox")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        d = json.loads(body)
        self.assertEqual(d["total"], len(d["stations"]))
        self.assertEqual({s["id"] for s in d["stations"]},
                         {"drums", "petuq", "gong", "melody", "cymbals", "costume", "mural", "guru"})

    def test_existing_routes_still_work(self):
        self.assertEqual(self.get("/avatar.png")[0], 200)
        self.assertEqual(json.loads(self.get("/api/cuq")[2])["scale"], cuq.SCALE)
        self.assertTrue(json.loads(self.get("/api/meta")[2])["topics"])
        status, d = self.post("/api/start", {})
        self.assertEqual(status, 200)
        status, d = self.post("/api/chat", {"thread_id": d["thread_id"], "message": "Sandbox"})
        self.assertEqual(status, 200)
        self.assertEqual(d["stage"], "menu")

    def test_3d_avatar_is_served_as_a_transparent_png(self):
        with urllib.request.urlopen(self.base + "/guru_3d.png", timeout=10) as r:
            self.assertEqual(r.status, 200)
            self.assertEqual(r.headers.get("Content-Type"), "image/png")
            data = r.read()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(data[25], 6)  # IHDR colour type 6 = RGBA, so the sprite has an alpha channel
        self.assertEqual(self.get("/avatar.png")[0], 200)  # the flat badge still works (favicon)

    def test_both_pages_use_the_3d_avatar_and_time_of_day_themes(self):
        status, ctype, js = self.get("/theme.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", ctype)
        self.assertIn("window.GBTheme", js)
        self.assertIn("getHours()", js)
        for name in ("'morning'", "'afternoon'", "'evening'", "'auto'", "localStorage"):
            self.assertIn(name, js)
        status, ctype, css = self.get("/theme.css")
        self.assertEqual(status, 200)
        self.assertIn("text/css", ctype)
        for theme in ("morning", "afternoon", "evening"):
            self.assertIn(f'[data-theme="{theme}"]', css)
        self.assertIn("backdrop-filter: blur(20px)", css)
        for path in ("/", "/chat"):
            page = self.get(path)[2]
            self.assertIn('src="/guru_3d.png"', page)
            self.assertIn('<link rel="stylesheet" href="/theme.css">', page)
            self.assertIn('<script src="/theme.js"></script>', page)
            self.assertIn("GBTheme.toggle(", page)
        chat = self.get("/chat")[2]
        self.assertIn('<img id="guru-puppet" class="guru-sprite" src="/guru_3d.png" alt="Guru Beleq"', chat)
        self.assertNotIn("<svg id=\"guru-puppet\"", chat)
        for state in ("idle", "listening", "greeting", "teaching", "celebrate", "thinking", "comfort", "six_seven"):
            self.assertIn(f"#avatar-stage.state-{state} .guru-sprite", chat)  # every reaction has its own animation
        self.assertIn("playDrumSound()", chat)
        self.assertIn('class="status-pill"', chat)

    def test_live_3d_avatar_script_is_served_with_png_fallback(self):
        status, ctype, js = self.get("/guru3d.js")
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "application/javascript; charset=utf-8")  # module scripts need a JS type
        self.assertIn("three@0.170.0", js)
        self.assertIn("window.Guru3D = api", js)
        for method in ("setReaction(", "setTheme(", "setListening(", "strike("):
            self.assertIn(method, js)
        for state in ("idle", "listening", "greeting", "teaching", "celebrate", "thinking", "comfort", "six_seven"):
            self.assertRegex(js, rf"\n  {state}\(t\) \{{")  # one 3D pose per reaction state
        self.assertIn("ACESFilmicToneMapping", js)
        self.assertIn("has-3d", js)            # the PNG is only hidden once the canvas has drawn
        self.assertIn("webglcontextlost", js)  # ... and comes back if the GPU context is lost
        chat = self.get("/chat")[2]
        self.assertIn('<script type="module" src="/guru3d.js"></script>', chat)
        self.assertIn('src="/guru_3d.png"', chat)  # fallback sprite still in the arch
        self.assertIn("if (window.Guru3D) window.Guru3D.setReaction(clean, speaking);", chat)
        self.assertNotIn("guru3d.js", self.get("/")[2])  # the landing page keeps the PNG

    def test_chat_reports_engine_and_mode(self):
        _, d = self.post("/api/start", {})
        self.assertIs(d["smart"], False)
        _, d = self.post("/api/chat", {"thread_id": d["thread_id"], "message": "Sandbox"})
        self.assertEqual(d["engine"], "python")
        self.assertIs(d["smart"], False)
        self.assertEqual(json.loads(self.get("/api/meta")[2])["llm"]["enabled"], False)

    def test_unknown_route_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.get("/nope")
        self.assertEqual(err.exception.code, 404)


# ---------- Smart Mode (Gemini), always mocked: no network calls ----------
SMART_ENV = {"GEMINI_API_KEY": "test-key", "GEMINI_ENABLED": "1", "GEMINI_MODEL": "gemini-2.5-flash"}
URLOPEN = "src.llm.urllib.request.urlopen"


def gemini_reply(text: str, finish: str = "STOP"):
    """A fake urlopen() result carrying a Gemini generateContent response."""
    resp = mock.MagicMock()
    resp.read.return_value = json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}]}).encode()
    cm = mock.MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = False
    return cm


def http_error(code: int, status: str = ""):
    body = io.BytesIO(json.dumps({"error": {"code": code, "status": status}}).encode())
    return urllib.error.HTTPError(llm.API_URL, code, "error", {}, body)


class SmartMode(Chat):
    QUESTION = "what does the petuq do?"
    GOOD = "The petuq, also called the oncer, sets the tempo, and the whole group follows its speed (Saputra, 2019)."

    def setUp(self):
        super().setUp()
        llm.reset()
        self.addCleanup(llm.reset)

    def classic(self, *turns):
        """What the rule-based engine says to the same turns, on a separate thread with Gemini off."""
        with mock.patch.dict(os.environ, {"GEMINI_ENABLED": "0"}):
            g, t = build_graph(), self.id() + ":classic"
            start(g, t)
            ask(g, "Budi", t)
            return [ask(g, x, t) for x in turns][-1]

    def test_missing_key_falls_back_without_calling_the_api(self):
        expected = self.classic(self.QUESTION)
        with mock.patch.dict(os.environ, {"GEMINI_ENABLED": "1"}), mock.patch(URLOPEN) as urlopen:
            os.environ.pop("GEMINI_API_KEY", None)
            self.assertFalse(llm.enabled())
            self.begin()
            self.assertEqual(self.say(self.QUESTION), expected)
            self.assertIsNone(llm.generate("system", "prompt"))
            urlopen.assert_not_called()
        self.assertEqual(self.state()["engine"], "python")

    def test_quota_429_falls_back_and_starts_cooldown(self):
        expected = self.classic(self.QUESTION, "what is the gong for?")
        with mock.patch.dict(os.environ, SMART_ENV), \
                mock.patch(URLOPEN, side_effect=http_error(429, "RESOURCE_EXHAUSTED")) as urlopen:
            self.begin()
            self.assertIn("(Saputra, 2019)", self.say(self.QUESTION))
            self.assertEqual(urlopen.call_count, 1)
            self.assertTrue(llm.cooling_down())
            self.assertFalse(llm.available())
            self.assertEqual(self.say("what is the gong for?"), expected)  # answered instantly by Python
            self.assertEqual(urlopen.call_count, 1)  # the cooldown skipped the API
            self.assertEqual(self.state()["engine"], "python")
            self.assertGreater(llm.status()["cooldown_seconds"], 0)

    def test_rejected_key_falls_back_silently_and_cools_down(self):
        expected = self.classic(self.QUESTION)
        for code, status in ((401, "UNAUTHENTICATED"), (403, "PERMISSION_DENIED")):
            llm.reset()
            with self.subTest(code=code), mock.patch.dict(os.environ, SMART_ENV), \
                    mock.patch(URLOPEN, side_effect=http_error(code, status)) as urlopen:
                self.tid = f"{self.id()}:{code}"
                self.begin()
                self.assertEqual(self.say(self.QUESTION), expected)
                self.assertTrue(llm.cooling_down())
                self.say("thank you")
                self.assertEqual(urlopen.call_count, 1)
                self.assertIn(f"HTTP {code}", llm.status()["last_error"])

    def test_timeout_network_and_server_errors_fall_back(self):
        expected = self.classic(self.QUESTION)
        self.begin()
        for failure in (socket.timeout("timed out"), TimeoutError(), urllib.error.URLError("no network"),
                        ConnectionResetError(), http_error(500, "INTERNAL"), http_error(503, "UNAVAILABLE")):
            with self.subTest(failure=type(failure).__name__), mock.patch.dict(os.environ, SMART_ENV), \
                    mock.patch(URLOPEN, side_effect=failure):
                self.assertEqual(self.say(self.QUESTION), expected)
                self.assertEqual(self.state()["engine"], "python")
                self.assertFalse(llm.cooling_down())  # only quota and key errors pause Gemini

    def test_malformed_or_cut_off_responses_give_none(self):
        bad = mock.MagicMock()
        bad.__enter__.return_value.read.return_value = b"not json"
        empty = mock.MagicMock()
        empty.__enter__.return_value.read.return_value = b'{"candidates": []}'
        with mock.patch.dict(os.environ, SMART_ENV):
            for resp in (bad, empty, gemini_reply(""), gemini_reply(self.GOOD, finish="MAX_TOKENS"), gemini_reply(self.GOOD, finish="SAFETY")):
                with mock.patch(URLOPEN, return_value=resp):
                    self.assertIsNone(llm.generate("system", "prompt"))

    def test_valid_reply_is_used_and_keeps_the_lesson_reprompt(self):
        with mock.patch.dict(os.environ, SMART_ENV), mock.patch(URLOPEN, return_value=gemini_reply(self.GOOD)) as urlopen:
            self.begin()
            self.say("lesson")
            lesson = self.state()["lesson"]
            question = get_topic(lesson["topic"])["lesson"][lesson["step"]]["question"]
            reply = self.say(self.QUESTION)
        self.assertTrue(reply.startswith(self.GOOD))
        self.assertTrue(reply.endswith(f"Now, back to our lesson: {question}"))
        self.assertEqual(self.state()["engine"], "gemini")
        self.assertEqual(self.state()["stage"], "lesson")
        self.assertEqual(self.state()["lesson"], lesson)  # asking a question doesn't use an attempt
        req = urlopen.call_args[0][0]
        self.assertIn("models/gemini-2.5-flash:generateContent", req.full_url)
        self.assertNotIn("test-key", req.full_url)  # the key travels in a header, not the URL
        self.assertEqual(req.get_header("X-goog-api-key"), "test-key")
        body = json.loads(req.data)
        system = body["systemInstruction"]["parts"][0]["text"]
        self.assertNotIn("system_instruction", body)
        self.assertIn("Budi", system)
        # the whole cited knowledge base goes along: every fact, glossary entry and reference
        for t in topics():
            for f in t["facts"]:
                self.assertIn(f["text"], system)
        for term, entry in glossary().items():
            self.assertIn(f"{term}: {entry['meaning']}", system)
        for r in references().values():
            self.assertIn(r["full"], system)
        prompt = body["contents"][0]["parts"][0]["text"]
        self.assertIn(question, prompt)  # told which lesson question not to give away
        self.assertIn("Budi: lesson", prompt)  # recent conversation for follow-ups

    def test_gemini_answers_open_requests_the_router_calls_offtopic(self):
        fact = "Here's one, Budi: the drums are carried on the players' shoulders in processions (Ministry of Tourism, n.d.)."
        decline = "That's outside what I teach, Budi, but I'd love to tell you how the gong closes each phrase."
        simple = "Simply put: two big drums lead, and gongs, cymbals and a flute join in (Saputra, 2019)."
        with mock.patch.dict(os.environ, SMART_ENV), mock.patch(URLOPEN) as urlopen:
            self.begin()
            for message, reply, intent in (("give me a fun fact", fact, "fun_fact"),
                                           ("What is the capital of France?", decline, "offtopic"),
                                           ("explain it simply", simple, "offtopic"),
                                           ("what are the instruments?", simple, "qa")):
                with self.subTest(message=message):
                    urlopen.return_value = gemini_reply(reply)
                    self.assertEqual(self.say(message), reply)
                    self.assertEqual(self.state()["intent"], intent)
                    self.assertEqual(self.state()["engine"], "gemini")
            prompt = json.loads(urlopen.call_args[0][0].data)["contents"][0]["parts"][0]["text"]
            self.assertIn("Budi: explain it simply", prompt)
            self.assertIn(simple, prompt)

    def test_classic_mode_gives_cited_fun_facts(self):
        self.begin()
        first = self.say("give me a fun fact")
        self.assertNotIn("outside what I teach", first)
        self.assertRegex(first, r"\(.+, (\d{4}|n\.d\.)\)")
        self.assertEqual(self.state()["intent"], "fun_fact")
        second = self.say("another one")
        self.assertEqual(self.state()["intent"], "fun_fact")
        self.assertNotEqual(first, second)  # unused facts first
        self.assertIn("(", self.say("surprise me"))

    def test_classic_fun_fact_inside_a_lesson_returns_to_the_question(self):
        self.begin()
        self.say("lesson")
        lesson = self.state()["lesson"]
        reply = self.say("tell me an interesting fact")
        self.assertIn("Here's a fun fact", reply)
        self.assertIn("Now, back to our lesson:", reply)
        self.assertEqual(self.state()["lesson"], lesson)

    def test_fun_fact_falls_back_to_classic_when_gemini_fails(self):
        with mock.patch.dict(os.environ, SMART_ENV), mock.patch(URLOPEN, side_effect=http_error(429, "RESOURCE_EXHAUSTED")):
            self.begin()
            reply = self.say("give me a fun fact")
        self.assertTrue(reply.startswith("Here's a fun fact, Budi:"))
        self.assertEqual(self.state()["engine"], "python")

    def test_invented_citations_are_rejected_and_real_styles_accepted(self):
        for text in ("The petuq keeps the tempo (Saputra, 2019).", "Saputra (2019) says the petuq keeps the tempo.",
                     "Drummers play interlocking patterns (Saputra, 2019; Keen, 2015).",
                     "Cohesion matters (Markarma et al., 2022). Visit Sade village (Ministry of Tourism, n.d.).",
                     "Hello Budi! What would you like to learn today?"):  # no citation needed for small talk
            self.assertTrue(llm.grounded(text), text)
        for text in ("The petuq keeps the beat (Smith, 2020).", "Saputra (2023) says so.",
                     "It keeps the tempo (Saputra, 2019; Wikipedia, 2023)."):
            self.assertFalse(llm.grounded(text), text)
        expected = self.classic(self.QUESTION)
        self.begin()
        with mock.patch.dict(os.environ, SMART_ENV), \
                mock.patch(URLOPEN, return_value=gemini_reply("The petuq keeps the beat (Smith, 2020).")):
            self.assertEqual(self.say(self.QUESTION), expected)
        self.assertIn("not in the knowledge base", llm.status()["last_error"])

    def test_http_400_on_thinking_config_retries_without_it(self):
        with mock.patch.dict(os.environ, SMART_ENV), \
                mock.patch(URLOPEN, side_effect=[http_error(400, "INVALID_ARGUMENT"), gemini_reply(self.GOOD)]) as urlopen:
            self.begin()
            self.assertEqual(self.say(self.QUESTION), self.GOOD)
            first, second = (json.loads(c[0][0].data)["generationConfig"] for c in urlopen.call_args_list)
            self.assertIn("thinkingConfig", first)
            self.assertNotIn("thinkingConfig", second)
            self.assertFalse(llm.cooling_down())

    def test_last_error_is_reported_without_the_key(self):
        body = io.BytesIO(json.dumps({"error": {"status": "INVALID_ARGUMENT", "message": "bad key test-key here"}}).encode())
        err = urllib.error.HTTPError(llm.API_URL, 400, "error", {}, body)
        with mock.patch.dict(os.environ, {**SMART_ENV, "GEMINI_MODEL": "gemini-2.0-flash"}), mock.patch(URLOPEN, side_effect=err):
            self.assertIsNone(llm.generate("system", "prompt"))
            status = llm.status()
        self.assertIn("HTTP 400 INVALID_ARGUMENT", status["last_error"])
        self.assertNotIn("test-key", json.dumps(status))
        self.assertIn("***", status["last_error"])

    def test_smalltalk_is_reworded_and_rule_flows_stay_python(self):
        warm = "It's my pleasure, Budi! Shall we explore the drums or the gongs next?"
        with mock.patch.dict(os.environ, SMART_ENV), mock.patch(URLOPEN, return_value=gemini_reply(warm)) as urlopen:
            self.begin()
            self.assertEqual(self.say("thank you"), warm)
            self.assertEqual(self.state()["engine"], "gemini")
            calls = urlopen.call_count
            self.assertIn("1. Start a lesson", self.say("menu"))  # deterministic flows never call Gemini
            self.say("quiz")
            self.say("skip")
            self.assertEqual(self.say("67").split("\n")[0], "🤲 67")
            self.assertEqual(urlopen.call_count, calls)
            self.assertEqual(self.state()["engine"], "python")

    def test_smalltalk_with_an_invented_citation_falls_back(self):
        with mock.patch.dict(os.environ, SMART_ENV), \
                mock.patch(URLOPEN, return_value=gemini_reply("You're welcome! Gongs are bronze (Gamelan Society, 2001).")):
            self.begin()
            self.assertIn("You're very welcome, Budi!", self.say("thank you"))

    def test_pages_hide_the_engine_and_show_a_thinking_indicator(self):
        root = Path(__file__).resolve().parent.parent / "web"
        for page in ("index.html", "sandbox.html"):
            html = (root / page).read_text(encoding="utf-8")
            with self.subTest(page=page):
                self.assertNotIn("Smart Mode", html)
                self.assertNotIn("Classic Mode", html)
                self.assertIn("Guru Beleq is thinking", html)
                self.assertIn("typing-dots", html)
        self.assertIn("setAvatarReaction('thinking', false)", (root / "index.html").read_text(encoding="utf-8"))
        app = (root.parent / "app.py").read_text(encoding="utf-8")
        self.assertIn('st.spinner(UI[current_lang()]["thinking"])', app)
        self.assertIn('"thinking": "Guru Beleq is thinking..."', app)

    def test_env_file_is_loaded_without_overriding_real_variables(self):
        path = os.path.join(_tmp, "test.env")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# comment\nGEMINI_TEST_A=abc\nexport GEMINI_TEST_B = \"quoted value\"\nGEMINI_TEST_C=from-file\n\nnot a line\n")
        with mock.patch.dict(os.environ, {"GEMINI_TEST_C": "real"}):
            llm.load_env(Path(path))
            self.assertEqual(os.environ["GEMINI_TEST_A"], "abc")
            self.assertEqual(os.environ["GEMINI_TEST_B"], "quoted value")
            self.assertEqual(os.environ["GEMINI_TEST_C"], "real")
        self.assertNotIn("GEMINI_TEST_A", os.environ)

    def test_env_example_exists_and_env_is_ignored(self):
        root = Path(__file__).resolve().parent.parent
        self.assertIn("GEMINI_API_KEY=", (root / ".env.example").read_text(encoding="utf-8"))
        self.assertIn(".env", (root / ".gitignore").read_text(encoding="utf-8").split())


if __name__ == "__main__":
    unittest.main()


# ---------- Bahasa Malaysia ----------
class MalayChat(Chat):
    def say(self, text, lang=None):
        return ask(self.graph, text, self.tid, lang)

    def begin(self, name="Siti", lang="ms"):
        start(self.graph, self.tid, lang)
        return self.say(name)

    def test_malay_knowledge_base_lines_up_with_the_english_one(self):
        self.assertEqual(validate(), [])
        ms = load_translation("ms")["topics"]
        for t in topics():
            m = get_topic(t["id"], "ms")
            self.assertEqual(len(m["facts"]), len(t["facts"]))
            self.assertEqual(len(m["lesson"]), len(t["lesson"]))
            self.assertNotEqual(m["title"], t["title"])
            self.assertEqual(ms[t["id"]]["title"], m["title"])
            for fe, fm in zip(t["facts"], m["facts"]):
                self.assertEqual(fe["sources"], fm["sources"])  # a translated fact keeps its citation
        self.assertEqual(set(glossary("ms")), set(glossary()))

    def test_greeting_name_and_menu_in_malay(self):
        start(self.graph, self.tid, "ms")
        self.assertEqual(self.state()["lang"], "ms")
        reply = self.say("nama saya Siti")
        self.assertEqual(self.state()["user_name"], "Siti")
        self.assertIn("Siti", reply)
        self.assertIn("Ini perkara yang boleh kita lakukan bersama", reply)
        for text, name in (("nama saya Aminah", "Aminah"), ("panggil saya Ali", "Ali"), ("saya Farid", "Farid")):
            self.assertEqual(persona.extract_name(text), name)

    def test_malay_greetings_follow_the_clock(self):
        with mock.patch.object(persona, "_part_of_day", return_value=0):
            self.assertTrue(persona.time_greeting("ms").startswith("Selamat pagi"))
        with mock.patch.object(persona, "_part_of_day", return_value=2):
            self.assertTrue(persona.time_greeting("ms").startswith("Selamat malam"))

    def test_questions_are_answered_in_malay_with_citations(self):
        self.begin()
        reply = self.say("apa fungsi petuq?")
        self.assertIn("rentak", reply)
        self.assertIn("(Saputra, 2019)", reply)
        english = self.say("what does the petuq do?")  # an English question still gets a Malay answer
        self.assertIn("rentak", english)
        self.assertNotIn("sets the tempo", english)

    def test_malay_lesson_accepts_malay_and_english_answers(self):
        self.begin()
        reply = self.say("1")
        self.assertIn("Pelajaran 1", reply)
        self.assertIn("pulau manakah", reply)
        self.say("petunjuk")
        self.assertEqual(self.state()["stage"], "lesson")
        self.assertEqual(self.state()["lesson"]["attempts"], 0)  # a hint does not use an attempt
        reply = self.say("masyarakat Sasak di Lombok")
        self.assertIn("Langkah 2", reply)
        reply = self.say("it means big drum")  # the English answer words are still accepted
        self.assertNotEqual(self.state()["stage"], "lesson")
        self.assertIn("overview", self.state()["progress"]["lessons_done"])

    def test_malay_quiz_hint_and_skip(self):
        self.begin()
        reply = self.say("kuiz")
        self.assertEqual(self.state()["stage"], "quiz")
        self.assertIn("kuiz", reply.lower())
        self.say("petunjuk")
        self.assertEqual(self.state()["stage"], "quiz")
        before = self.state()["quiz"]
        self.say("langkau")
        self.assertNotEqual(self.state()["quiz"], before)

    def test_malay_fun_facts_and_another_one(self):
        self.begin()
        self.assertEqual(nlp.correct_spelling("beri saya fakta menarik", "ms"), "beri saya fakta menarik")
        first = self.say("beri saya fakta menarik")
        self.assertRegex(first, r"\([A-Z][^()]*, (\d{4}|n\.d\.)\)")  # Harvard citation
        self.assertTrue(first.startswith("Ini satu fakta menarik, Siti"))
        second = self.say("satu lagi")
        self.assertNotEqual(first, second)

    def test_switching_language_mid_lesson_repeats_the_question(self):
        start(self.graph, self.tid, "en")
        self.say("Budi")
        question_en = self.say("lesson")
        self.assertIn("Which people does the Gendang Beleq belong to", question_en)
        reply = switch_language(self.graph, self.tid, "ms")
        self.assertTrue(reply.startswith(i18n.t("ms", "switched")))
        self.assertIn("pulau manakah", reply)
        self.assertEqual(self.state()["stage"], "lesson")
        self.assertEqual(self.state()["lesson"]["attempts"], 0)  # switching does not use an attempt
        back = switch_language(self.graph, self.tid, "en")
        self.assertIn("Which people does the Gendang Beleq belong to", back)

    def test_english_is_the_default(self):
        start(self.graph, self.tid)
        self.assertEqual(self.state()["lang"], "en")
        self.assertIn("Here is what we can do together", self.say("Budi"))

    def test_avatar_reactions_understand_malay_replies(self):
        self.begin()
        self.say("1")
        reply = self.say("masyarakat Sasak di Lombok")
        self.assertEqual(persona.reaction_of(self.state(), reply), "celebrate")

    def test_gemini_prompt_in_malay_uses_the_malay_facts(self):
        llm.reset()
        self.addCleanup(llm.reset)
        good = "Petuq menetapkan rentak, dan semua orang mengikut kelajuannya (Saputra, 2019)."
        with mock.patch.dict(os.environ, SMART_ENV), mock.patch(URLOPEN, return_value=gemini_reply(good)) as urlopen:
            self.begin()
            self.say("apa fungsi petuq?")
        system = json.loads(urlopen.call_args[0][0].data)["systemInstruction"]["parts"][0]["text"]
        self.assertIn(llm.LANGUAGE_RULES["ms"], system)
        for f in get_topic("instruments", "ms")["facts"]:
            self.assertIn(f["text"], system)


class MalayWeb(WebRoutes):
    def test_language_routes(self):
        _, d = self.post("/api/start", {"lang": "ms"})
        self.assertEqual(d["lang"], "ms")
        self.assertIn("Saya Guru Beleq", d["reply"])
        tid = d["thread_id"]
        _, d = self.post("/api/chat", {"thread_id": tid, "message": "Siti", "lang": "ms"})
        self.assertEqual(d["stage"], "menu")
        _, d = self.post("/api/language", {"thread_id": tid, "lang": "en"})
        self.assertEqual(d["lang"], "en")
        self.assertTrue(d["reply"].startswith("Sure, let's continue in English!"))
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.post("/api/language", {"thread_id": "no-such-thread", "lang": "ms"})
        self.assertEqual(err.exception.code, 404)

    def test_get_routes_in_malay(self):
        meta = json.loads(self.get("/api/meta?lang=ms")[2])
        self.assertEqual(meta["topics"][0]["title"], get_topic("overview", "ms")["title"])
        self.assertEqual(json.loads(self.get("/api/cuq?lang=ms")[2])["items"], cuq.ITEMS_MS)
        stations = json.loads(self.get("/api/sandbox?lang=ms")[2])
        self.assertEqual(stations["lang"], "ms")
        self.assertEqual(len(stations["stations"]), 8)

    def test_every_page_loads_the_language_switch(self):
        status, ctype, body = self.get("/lang.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", ctype)
        self.assertIn("window.GBLang", body)
        for path in ("/", "/chat", "/sandbox"):
            page = self.get(path)[2]
            self.assertIn('<script src="/lang.js"></script>', page)
            self.assertIn("GBLang.toggle(", page)
            self.assertIn("ms: {", page)
            self.assertIn("data-lang-link", page)

    def test_mascot_is_centred_in_its_window_panel(self):
        page = self.get("/chat")[2]
        self.assertIn("--side-w:", page)
        self.assertIn("width:var(--side-w)", page)  # the window panel ...
        self.assertIn("grid-template-columns: var(--side-w)", page)  # ... and the avatar column share one width
        stage = page[page.index("#avatar-stage {"):]
        stage = stage[:stage.index("}")]
        self.assertIn("justify-content:center", stage)
        self.assertNotIn("flex-end", stage)
