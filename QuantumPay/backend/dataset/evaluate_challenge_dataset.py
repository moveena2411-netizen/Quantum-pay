import csv
from itertools import product

from challenge_engine import ChallengeEngine


DATASET = "dataset/risk_evaluation_dataset.csv"


def find_answers_for_score(target_score):
    """
    Find a valid combination of challenge answers
    that produces the target challenge score.
    """

    question_ids = [
        "q1",
        "q2",
        "q4",
        "q5",
        "q6",
        "q7",
        "q8",
        "q9",
        "q10",
    ]

    for values in product([False, True], repeat=len(question_ids)):

        answers = dict(zip(question_ids, values))

        result = ChallengeEngine.analyze_answers(answers)

        if result.challenge_score == target_score:
            return answers

    return None


def main():

    total = 0
    passed = 0
    failed = 0

    with open(DATASET, newline="", encoding="utf-8") as file:

        rows = csv.DictReader(file)

        for row in rows:

            if row["initial_risk"] != "HIGH":
                continue

            total += 1

            expected_score = int(row["challenge_score"])
            expected_risk = row["final_risk"]

            answers = find_answers_for_score(
                expected_score
            )

            if answers is None:
                print(
                    "Could not construct answers for score:",
                    expected_score
                )
                failed += 1
                continue

            result = ChallengeEngine.analyze_answers(
                answers
            )

            if (
                result.challenge_score == expected_score
                and result.final_risk == expected_risk
            ):
                passed += 1
            else:
                failed += 1

                print(
                    "Mismatch:",
                    row["transaction_id"],
                    "Expected score:",
                    expected_score,
                    "Actual score:",
                    result.challenge_score,
                    "Expected risk:",
                    expected_risk,
                    "Actual risk:",
                    result.final_risk,
                )

    print("--------------------------------")
    print("QuantumPay Challenge Evaluation")
    print("--------------------------------")
    print("HIGH cases tested :", total)
    print("Passed            :", passed)
    print("Failed            :", failed)

    if total > 0:
        agreement = (passed / total) * 100
        print(f"Agreement         : {agreement:.2f}%")

    print("--------------------------------")


if __name__ == "__main__":
    main()