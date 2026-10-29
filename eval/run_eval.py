"""Run every question in eval/questions.csv through the bot, check the intent automatically and save answers
for manual scoring.

Score each row on: accuracy, behaviour. Run: python -m eval.run_eval
"""
import os
import tempfile

import pandas as pd

os.environ.setdefault("PROFILES_FILE", os.path.join(tempfile.mkdtemp(), "profiles.json"))  # don't touch real profiles

from src.graph import ask, build_graph, start, state_of  # noqa: E402


def main() -> None:
    graph = build_graph()
    df = pd.read_csv("eval/questions.csv").fillna("")
    answers, intents = [], []
    for i, q in zip(df["id"], df["question"]):
        thread = f"eval-{i}"
        start(graph, thread)
        ask(graph, "Tester", thread)  # tell the bot our name
        answers.append(ask(graph, q, thread))
        intents.append(state_of(graph, thread).get("intent", ""))
    df["bot_answer"], df["actual_intent"] = answers, intents
    df["intent_match"] = [("" if not e else "y" if e == a else "n") for e, a in zip(df["expected_intent"], intents)]
    for col in ("accuracy_0_2", "behavior_ok_y_n"):
        df[col] = ""
    df.to_csv("eval/results.csv", index=False)
    checked = df[df["expected_intent"] != ""]
    print(f"Intent routing: {(checked['intent_match'] == 'y').sum()}/{len(checked)} correct")
    print("Saved eval/results.csv; fill in the score columns by hand.")


if __name__ == "__main__":
    main()
