from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from challenge_engine import ChallengeEngine


def main():
    questions = ChallengeEngine.get_questions()
    assert len(questions) == 6, len(questions)

    safe = {
        "q1": True,
        "q2": True,
        "q3": True,
        "q4": False,
        "q5": False,
        "q6": True,
    }
    safe_result = ChallengeEngine.analyze_answers(safe)
    assert safe_result.final_risk == "MEDIUM"
    assert safe_result.challenge_score == 0

    risky = {
        "q1": False,
        "q2": False,
        "q3": False,
        "q4": True,
        "q5": True,
        "q6": False,
    }
    risky_result = ChallengeEngine.analyze_answers(risky)
    assert risky_result.final_risk == "HIGH"
    assert risky_result.challenge_score == 8

    print("Challenge questions:", len(questions))
    print("SAFE ->", safe_result)
    print("RISKY ->", risky_result)
    print("Challenge flow test PASSED")


if __name__ == "__main__":
    main()
