"""Chatbot Usability Questionnaire (CUQ) for the Chapter 4 usability test.

Instrument: Holmes, S., Moorhead, A., Bond, R., Zheng, H., Coates, V. and McTear, M. (2019) 'Usability testing of a
healthcare chatbot: Can we use conventional methods to assess conversational user interfaces?', Proceedings of the
31st European Conference on Cognitive Ergonomics, pp. 207-214. doi:10.1145/3335082.3335094.

Score = ((sum of odd items - 8) + (40 - sum of even items)) / 64 * 100

Run:  python -m eval.cuq collect     one tester answers in the terminal
      python -m eval.cuq report      summary of all responses so far
"""
import csv
import os
import statistics
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# odd items are positive statements, even items are negative
ITEMS = [
    "The chatbot's personality was realistic and engaging",
    "The chatbot seemed too robotic",
    "The chatbot was welcoming during initial setup",
    "The chatbot seemed very unfriendly",
    "The chatbot explained its scope and purpose well",
    "The chatbot gave no indication as to its purpose",
    "The chatbot was easy to navigate",
    "It would be easy to get confused when using the chatbot",
    "The chatbot understood me well",
    "The chatbot failed to recognise a lot of my inputs",
    "Chatbot responses were useful, appropriate and informative",
    "Chatbot responses were irrelevant",
    "The chatbot coped well with any errors or mistakes",
    "The chatbot seemed unable to handle any errors",
    "The chatbot was very easy to use",
    "The chatbot was very complex",
]
SCALE = "1 = strongly disagree, 2 = disagree, 3 = neutral, 4 = agree, 5 = strongly agree"
COLUMNS = ["respondent", *(f"Q{i}" for i in range(1, 17)), "cuq_score", "comments"]


def _file() -> Path:
    return Path(os.getenv("CUQ_FILE", ROOT / "eval" / "cuq_responses.csv"))


def score(answers: list[int]) -> float:
    """CUQ score out of 100 from the 16 answers, in questionnaire order."""
    if len(answers) != 16 or any(a not in (1, 2, 3, 4, 5) for a in answers):
        raise ValueError("CUQ needs 16 answers, each from 1 to 5")
    positive, negative = sum(answers[0::2]), sum(answers[1::2])
    return ((positive - 8) + (40 - negative)) / 64 * 100


def save(answers: list[int], comments: str = "") -> float:
    """Append one anonymous response and return its score."""
    result = score(answers)
    f = _file()
    new = not f.exists()
    with f.open("a", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        if new:
            writer.writerow(COLUMNS)
        writer.writerow([uuid.uuid4().hex[:8], *answers, round(result, 2), comments])
    return result


def load() -> list[dict]:
    try:
        with _file().open(newline="", encoding="utf-8") as src:
            return list(csv.DictReader(src))
    except FileNotFoundError:
        return []


def summarise(rows: list[dict]) -> dict | None:
    """Overall score plus the mean of each item, which shows where to improve."""
    if not rows:
        return None
    scores = [float(r["cuq_score"]) for r in rows]
    return {
        "n": len(rows),
        "mean": statistics.mean(scores),
        "sd": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "min": min(scores),
        "max": max(scores),
        "items": [statistics.mean(int(r[f"Q{i}"]) for r in rows) for i in range(1, 17)],
    }


def report() -> None:
    s = summarise(load())
    if s is None:
        print("No responses yet. Run: python -m eval.cuq collect, or use the form in the app sidebar.")
        return
    print(f"Responses: {s['n']}")
    print(f"CUQ score: mean {s['mean']:.1f}, SD {s['sd']:.1f}, range {s['min']:.1f} to {s['max']:.1f} (out of 100)")
    print("\nItem means (odd items: higher is better; even items: lower is better)")
    for i, (item, mean) in enumerate(zip(ITEMS, s["items"]), start=1):
        print(f"  Q{i:<2} {mean:.2f}  {item}")


def collect() -> None:
    print(f"Chatbot Usability Questionnaire\n{SCALE}\n")
    answers = []
    for i, item in enumerate(ITEMS, start=1):
        while True:
            value = input(f"Q{i}. {item}: ").strip()
            if value in ("1", "2", "3", "4", "5"):
                answers.append(int(value))
                break
            print("Please type a number from 1 to 5.")
    comments = input("Any comments? (optional): ").strip()
    print(f"\nCUQ score: {save(answers, comments):.1f} out of 100. Saved to {_file()}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "report"
    {"collect": collect, "report": report}.get(command, report)()
