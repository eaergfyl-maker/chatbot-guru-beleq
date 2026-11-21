"""Languages: English ("en", the default) and Bahasa Malaysia ("ms").

Every sentence the rule-based engine says is here once per language; nodes pick it with t(lang, key, ...).
The knowledge base text in Malay lives in data/knowledge/topics_ms.json (see src/knowledge.py).
"""
LANGS = ("en", "ms")
DEFAULT = "en"


def norm(lang) -> str:
    """'ms', 'bm', 'ms-MY', 'malay' -> 'ms'; anything else -> 'en'."""
    low = str(lang or "").strip().lower()
    return "ms" if low[:2] in ("ms", "bm", "my") or low.startswith("malay") or low.startswith("bahasa") else DEFAULT


def opt(lang):
    """Like norm(), but keeps None (meaning: no change, use the language the conversation already has)."""
    return None if lang in (None, "") else norm(lang)


MESSAGES = {
    "en": {
        "reject.empty": "I didn't catch anything there. Could you type your message again?",
        "reject.too_long": "That message is a bit long for me. Could you shorten it to one or two sentences?",
        "reject.gibberish": "I couldn't make sense of that. Could you rephrase it in a sentence?",
        "error": "Sorry, something went wrong on my side. Could you try that again?",
        "bot_meaning": "'Guru' is Indonesian for teacher and 'beleq' is Sasak for big, so I am the Big Teacher",
        "greet": "{greeting}! I'm {bot}, your Gendang Beleq teacher. ({meaning}.) Before we begin, what should I call you?",
        "ask_name": "Before we begin, what should I call you?",
        "name_retry": "Sorry, I didn't catch your name. What should I call you? Just your first name is fine.",
        "welcome_back": "Welcome back, {name}! You have completed {done} of {total} lessons so far.",
        "nice_to_meet": "Nice to meet you, {name}!",
        "menu": (
            "Here is what we can do together, {name}:\n"
            "  1. Start a lesson (I teach you step by step)\n"
            "  2. Ask me anything about the Gendang Beleq\n"
            "  3. Take a quiz\n"
            "  4. Get a recommendation on what to learn next\n"
            "  5. See your progress\n"
            "  6. Help\n"
            "  7. See the sources behind what I teach\n"
            "  8. Browse the Sasak glossary\n"
            "  0. Say goodbye\n"
            "Type a number, or simply tell me in your own words what you would like."
        ),
        "wrong_number": "That number isn't on the menu.\n\n",
        "leave": "No problem, {name}. We can pick it up whenever you like.\n\n{menu}",
        "sources": "Everything I teach comes from these sources, {name}:\n{lines}\n\nWhat would you like to explore?",
        "glossary": "Here is the Sasak and musical glossary, {name}:\n{lines}\n\nAsk me about any term or topic to learn more!",
        "glossary_doc": "{Term} is {meaning}.",
        "invite": ("Ask away, {name}! You can ask about the name, the instruments, when it is played, its history "
                   "or the players. What would you like to know?"),
        "help": (
            "Just talk to me like you would to a teacher. I understand small typos and different wordings. "
            "Say 'lesson' to learn step by step, 'quiz' to test yourself, 'progress' for your report card, "
            "'sources' for my references, 'glossary' for Sasak terms, or ask any question. Inside a lesson or quiz "
            "you can say 'hint', 'skip', 'repeat' or 'stop'. Type 'menu' at any time to see the options."
        ),
        "struggling": ("{comfort} We can go slowly, {name}. Say 'lesson' and I will explain one small step at a time, "
                       "with hints whenever you want them."),
        "identity": ("I'm {bot}, a teaching chatbot built to explain the Gendang Beleq. {meaning}. "
                     "What would you like to learn, {name}?"),
        "decline": "That's fine, {name}. Ask me anything when you're ready, or say 'menu' to see the options.",
        "thanks": "You're very welcome, {name}! What would you like to explore next?",
        "hello": "{greeting}, {name}! Good to see you. What would you like to learn about the Gendang Beleq today?",
        "enjoying": "Glad you're enjoying it, {name}! What would you like to explore next?",
        "offtopic": ("That's outside what I teach, {name}. I'm here for the Gendang Beleq drum ensemble of Lombok. "
                     "What would you like to know about its history, instruments or ceremonies?"),
        "fun_fact": "Here's a fun fact, {name}: {fact} {cite}\n\nWant another one? Just ask!",
        "bye": ("Goodbye, {name}! You have completed {done} of {total} lessons and earned the title '{badge}'. "
                "Have a lovely {period}, and come back soon!"),
        "back_lesson": "\n\nNow, back to our lesson: {question}",
        "back_quiz": "\n\nNow, back to the quiz: {question}",
        "heard": "(I read that as: \"{heard}\")\n",
        "not_sure": ("I'm not sure about that one, {name}, and I'd rather not guess. "
                     "I can teach you about topics like {titles}. What would you like to look at?"),
        "what_else": "What else would you like to know?",
        "related": "Related lessons: {related}. What would you like to explore next?",
        "partial": "I don't have an exact answer to that, but this is the closest I can tell you: ",
        "present": "Step {n} of {total}\n{teach}\n\nNow it's your turn: {question}",
        "all_lessons_done": ("You have finished every lesson, {name}! Say 'quiz' to test everything you have learned, "
                             "or ask me any question."),
        "lesson_start": ("Let's begin, {name}! Lesson {number}: {title}\n"
                         "I'll teach a little, then ask you a question. Say 'hint' if you need a clue.\n\n"),
        "onward_next": "When you're ready, say 'lesson' to continue with '{title}', or 'quiz' to test yourself.",
        "onward_done": "You have now finished all the lessons! Say 'quiz' to test everything you learned.",
        "lesson_complete": "{feedback}\n\nLesson complete, {name}! Quick recap: {summary} {cite}\n{onward}",
        "repeat": "Of course! Here it is again.\n\n{step}",
        "clue": "Here's a clue: {hint}",
        "partly": "You've got part of it, {name}.",
        "lesson_retry": "{tone} Here's a clue: {hint}\nTry again in your own words.",
        "learn_together": "No problem, let's learn it together. {explain}",
        "quiz_start": ("Quiz time, {name}! I'll ask up to {n} questions. Answer in your own words. "
                       "Say 'hint' for a clue, 'skip' to pass, or 'stop' to quit.\n\nQuestion 1: {question}"),
        "quiz_retry": "{tone} Here's a clue: {hint}\nGive it one more try.",
        "answer_was": "The answer was: {explain}",
        "quiz_high": "Fantastic work!",
        "quiz_mid": "Good progress!",
        "quiz_low": "Keep practising, a lesson will help.",
        "quiz_done": ("{feedback}\n\nQuiz finished! You got {right} out of {n}. {comment} "
                      "Your title is now '{badge}'."),
        "quiz_next": "{feedback}\n\nQuestion {n}: {question}",
        "report": ("Report card for {name}\n"
                   "  Lessons completed: {done} of {total}{titles}\n"
                   "  Lesson questions right first time: {lesson_right} of {lesson_total}\n"
                   "  Quiz: {quiz_right} of {quiz_total} correct ({acc})\n"
                   "  Title: {badge}\n{next}"),
        "no_quiz": "no quiz taken yet",
        "next_up": "Next up: {title}.",
        "finished_all": "You have finished every lesson!",
        "why_new": "you haven't done this lesson yet",
        "why_interest": "it matches your interest in {keyword}",
        "why_practice": "the quiz showed it needs more practice",
        "why_asked": "you asked about it earlier",
        "covered_all": ("You've covered everything, {name}! A quiz is the best way to keep it fresh. "
                        "Is there any part you'd like to revisit?"),
        "recommend": ("Based on what you've done so far, I recommend:\n{lines}\n\n"
                      "Tell me which one appeals to you, or what you're curious about, and I'll start from there."),
        "switched": "Sure, let's continue in English!",
        "periods": ("morning", "afternoon", "evening"),
        "greetings": ("Good morning", "Good afternoon", "Good evening"),
        "praise": ["Excellent!", "Well done!", "Spot on!", "That's right!", "Great job!", "Exactly!"],
        "gentle": ["Not quite, but you're on the right track.", "Close! Keep thinking.", "Good effort, let's refine it."],
        "comfort": ["No worries, everyone learns at their own pace.", "That's okay, we'll take it slowly."],
        "badges": ("Curious Listener", "Apprentice Drummer", "Gong Keeper", "Master of the Big Drum"),
    },
    "ms": {
        "reject.empty": "Saya tidak menangkap apa-apa. Boleh taip mesej anda sekali lagi?",
        "reject.too_long": "Mesej itu agak panjang untuk saya. Boleh pendekkan kepada satu atau dua ayat?",
        "reject.gibberish": "Saya tidak faham maksudnya. Boleh tulis semula dalam satu ayat?",
        "error": "Maaf, ada masalah di pihak saya. Boleh cuba sekali lagi?",
        "bot_meaning": "'Guru' bermaksud pengajar dan 'beleq' ialah perkataan Sasak untuk besar, jadi sayalah Guru Besar",
        "greet": ("{greeting}! Saya {bot}, guru Gendang Beleq anda. ({meaning}.) "
                  "Sebelum kita mula, apakah nama yang patut saya panggil anda?"),
        "ask_name": "Sebelum kita mula, apakah nama yang patut saya panggil anda?",
        "name_retry": ("Maaf, saya tidak menangkap nama anda. Apakah nama yang patut saya panggil anda? "
                       "Nama pertama sahaja sudah memadai."),
        "welcome_back": "Selamat kembali, {name}! Setakat ini anda telah menamatkan {done} daripada {total} pelajaran.",
        "nice_to_meet": "Gembira berkenalan dengan anda, {name}!",
        "menu": (
            "Ini perkara yang boleh kita lakukan bersama, {name}:\n"
            "  1. Mulakan pelajaran (saya ajar anda langkah demi langkah)\n"
            "  2. Tanya saya apa sahaja tentang Gendang Beleq\n"
            "  3. Ambil kuiz\n"
            "  4. Dapatkan cadangan tentang apa yang patut dipelajari seterusnya\n"
            "  5. Lihat kemajuan anda\n"
            "  6. Bantuan\n"
            "  7. Lihat sumber di sebalik apa yang saya ajar\n"
            "  8. Layari glosari Sasak\n"
            "  0. Ucap selamat tinggal\n"
            "Taip nombor, atau beritahu saya dengan kata-kata anda sendiri apa yang anda mahu."
        ),
        "wrong_number": "Nombor itu tiada dalam menu.\n\n",
        "leave": "Tiada masalah, {name}. Kita boleh sambung bila-bila masa anda mahu.\n\n{menu}",
        "sources": "Semua yang saya ajar datang daripada sumber-sumber ini, {name}:\n{lines}\n\nApakah yang anda ingin terokai?",
        "glossary": ("Ini glosari istilah Sasak dan muzik, {name}:\n{lines}\n\n"
                     "Tanya saya tentang mana-mana istilah atau topik untuk mengetahui lebih lanjut!"),
        "glossary_doc": "{Term} ialah {meaning}.",
        "invite": ("Silakan bertanya, {name}! Anda boleh bertanya tentang namanya, alat-alat muziknya, bila ia "
                   "dimainkan, sejarahnya atau para pemainnya. Apakah yang anda ingin tahu?"),
        "help": (
            "Bercakaplah dengan saya seperti anda bercakap dengan seorang guru. Saya faham kesilapan ejaan kecil dan "
            "cara penyampaian yang berbeza. Sebut 'pelajaran' untuk belajar langkah demi langkah, 'kuiz' untuk menguji "
            "diri, 'kemajuan' untuk kad laporan anda, 'sumber' untuk rujukan saya, 'glosari' untuk istilah Sasak, atau "
            "tanya apa-apa soalan. Dalam pelajaran atau kuiz, anda boleh sebut 'petunjuk', 'langkau', 'ulang' atau "
            "'berhenti'. Taip 'menu' pada bila-bila masa untuk melihat pilihan."
        ),
        "struggling": ("{comfort} Kita boleh pergi perlahan-lahan, {name}. Sebut 'pelajaran' dan saya akan terangkan "
                       "satu langkah kecil pada satu masa, dengan petunjuk bila-bila masa anda mahu."),
        "identity": ("Saya {bot}, chatbot pengajar yang dibina untuk menerangkan Gendang Beleq. {meaning}. "
                     "Apakah yang anda ingin pelajari, {name}?"),
        "decline": "Tidak mengapa, {name}. Tanya saya apa sahaja apabila anda sudah bersedia, atau sebut 'menu' untuk melihat pilihan.",
        "thanks": "Sama-sama, {name}! Apakah yang anda ingin terokai seterusnya?",
        "hello": "{greeting}, {name}! Gembira berjumpa anda. Apakah yang anda ingin pelajari tentang Gendang Beleq hari ini?",
        "enjoying": "Saya gembira anda menikmatinya, {name}! Apakah yang anda ingin terokai seterusnya?",
        "offtopic": ("Itu di luar apa yang saya ajar, {name}. Saya di sini untuk ensembel gendang Gendang Beleq dari "
                     "Lombok. Apakah yang anda ingin tahu tentang sejarah, alat muzik atau upacaranya?"),
        "fun_fact": "Ini satu fakta menarik, {name}: {fact} {cite}\n\nMahu satu lagi? Tanya sahaja!",
        "bye": ("Selamat tinggal, {name}! Anda telah menamatkan {done} daripada {total} pelajaran dan memperoleh "
                "gelaran '{badge}'. Semoga {period} anda menyeronokkan, dan datanglah lagi!"),
        "back_lesson": "\n\nSekarang, kembali kepada pelajaran kita: {question}",
        "back_quiz": "\n\nSekarang, kembali kepada kuiz: {question}",
        "heard": "(Saya faham itu sebagai: \"{heard}\")\n",
        "not_sure": ("Saya kurang pasti tentang itu, {name}, dan saya tidak mahu meneka. "
                     "Saya boleh ajar anda tentang topik seperti {titles}. Apakah yang anda ingin lihat?"),
        "what_else": "Apa lagi yang anda ingin tahu?",
        "related": "Pelajaran berkaitan: {related}. Apakah yang anda ingin terokai seterusnya?",
        "partial": "Saya tiada jawapan yang tepat untuk itu, tetapi ini yang paling hampir yang boleh saya beritahu: ",
        "present": "Langkah {n} daripada {total}\n{teach}\n\nSekarang giliran anda: {question}",
        "all_lessons_done": ("Anda telah menamatkan setiap pelajaran, {name}! Sebut 'kuiz' untuk menguji semua yang "
                             "telah anda pelajari, atau tanya saya apa-apa soalan."),
        "lesson_start": ("Mari kita mulakan, {name}! Pelajaran {number}: {title}\n"
                         "Saya akan ajar sedikit, kemudian tanya anda satu soalan. Sebut 'petunjuk' jika anda perlukan klu.\n\n"),
        "onward_next": "Apabila anda bersedia, sebut 'pelajaran' untuk meneruskan dengan '{title}', atau 'kuiz' untuk menguji diri.",
        "onward_done": "Anda kini telah menamatkan semua pelajaran! Sebut 'kuiz' untuk menguji semua yang anda pelajari.",
        "lesson_complete": "{feedback}\n\nPelajaran selesai, {name}! Ringkasan: {summary} {cite}\n{onward}",
        "repeat": "Sudah tentu! Ini sekali lagi.\n\n{step}",
        "clue": "Ini petunjuknya: {hint}",
        "partly": "Anda betul sebahagiannya, {name}.",
        "lesson_retry": "{tone} Ini petunjuknya: {hint}\nCuba lagi dengan kata-kata anda sendiri.",
        "learn_together": "Tiada masalah, mari kita belajar bersama. {explain}",
        "quiz_start": ("Masa untuk kuiz, {name}! Saya akan tanya sehingga {n} soalan. Jawab dengan kata-kata anda "
                       "sendiri. Sebut 'petunjuk' untuk klu, 'langkau' untuk melangkau, atau 'berhenti' untuk keluar."
                       "\n\nSoalan 1: {question}"),
        "quiz_retry": "{tone} Ini petunjuknya: {hint}\nCuba sekali lagi.",
        "answer_was": "Jawapannya ialah: {explain}",
        "quiz_high": "Kerja yang hebat!",
        "quiz_mid": "Kemajuan yang baik!",
        "quiz_low": "Teruskan berlatih, pelajaran akan membantu.",
        "quiz_done": ("{feedback}\n\nKuiz tamat! Anda mendapat {right} daripada {n}. {comment} "
                      "Gelaran anda kini '{badge}'."),
        "quiz_next": "{feedback}\n\nSoalan {n}: {question}",
        "report": ("Kad laporan untuk {name}\n"
                   "  Pelajaran selesai: {done} daripada {total}{titles}\n"
                   "  Soalan pelajaran betul pada cubaan pertama: {lesson_right} daripada {lesson_total}\n"
                   "  Kuiz: {quiz_right} daripada {quiz_total} betul ({acc})\n"
                   "  Gelaran: {badge}\n{next}"),
        "no_quiz": "belum ada kuiz diambil",
        "next_up": "Seterusnya: {title}.",
        "finished_all": "Anda telah menamatkan setiap pelajaran!",
        "why_new": "anda belum membuat pelajaran ini",
        "why_interest": "ia sepadan dengan minat anda tentang {keyword}",
        "why_practice": "kuiz menunjukkan ia memerlukan lebih banyak latihan",
        "why_asked": "anda bertanya tentangnya tadi",
        "covered_all": ("Anda telah meliputi semuanya, {name}! Kuiz ialah cara terbaik untuk mengekalkan ingatan. "
                        "Adakah bahagian yang anda ingin ulang kaji?"),
        "recommend": ("Berdasarkan apa yang telah anda lakukan setakat ini, saya cadangkan:\n{lines}\n\n"
                      "Beritahu saya yang mana menarik minat anda, atau apa yang anda ingin tahu, dan saya akan mulakan dari situ."),
        "switched": "Baiklah, kita teruskan dalam Bahasa Malaysia!",
        "periods": ("pagi", "petang", "malam"),
        "greetings": ("Selamat pagi", "Selamat petang", "Selamat malam"),
        "praise": ["Hebat!", "Syabas!", "Tepat sekali!", "Betul!", "Bagus!", "Tepat!"],
        "gentle": ["Belum tepat, tetapi anda di landasan yang betul.", "Hampir! Teruskan berfikir.",
                   "Usaha yang baik, mari kita perbaiki."],
        "comfort": ["Jangan risau, setiap orang belajar mengikut kadar sendiri.", "Tidak mengapa, kita ambil perlahan-lahan."],
        "badges": ("Pendengar Ingin Tahu", "Pemain Gendang Perantis", "Penjaga Gong", "Pakar Gendang Besar"),
    },
}


def get(lang: str, key: str):
    """The raw entry (string, list or tuple) for a key, falling back to English."""
    return MESSAGES.get(norm(lang), MESSAGES[DEFAULT]).get(key, MESSAGES[DEFAULT][key])


def t(lang: str, key: str, **values) -> str:
    text = get(lang, key)
    return text.format(**values) if values else text


def all_values(key: str) -> list:
    """The entry for a key in every language, e.g. all praise phrases (for reaction matching)."""
    out = []
    for lang in LANGS:
        v = MESSAGES[lang][key]
        out += list(v) if isinstance(v, (list, tuple)) else [v]
    return out
