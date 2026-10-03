import csv
import random

from challenge_engine import ChallengeEngine


DATASET = "dataset/risk_evaluation_dataset.csv"


def main():
    total = 0
    passed = 0

    random.seed(42)

    with open(DATASET, newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)

        for row in rows:

            if row["initial_risk"] != "HIGH":
                continue

            total += 1

            answers = {
                "q1": random.random() >= 0.15,
                "q2": random.random() >= 0.20,
                "q4": random.random() < 0.18,
                "q5": random.random() < 0.15,
                "q6": random.random() >= 0.18,
                "q7": random.random() < 0.15,
                "q8": random.random() < 0.10,
                "q9": random.random() < 0.08,
                "q10": random.random() < 0.10,
            }

            result = ChallengeEngine.analyze_answers(
                answers
            )

            if result.final_risk == row["final_risk"]:
                passed += 1

    print("--------------------------------")
    print("QuantumPay Challenge Evaluation")
    print("--------------------------------")
    print("HIGH cases tested :", total)
    print("Passed            :", passed)
    print("Failed            :", total - passed)

    if total > 0:
        agreement = (passed / total) * 100
        print(f"Agreement         : {agreement:.2f}%")

    print("--------------------------------")


if __name__ == "__main__":
    main()