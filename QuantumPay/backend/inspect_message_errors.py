import csv

from message_analyzer import MessageAnalyzer


DATASET = "dataset/message_dataset.csv"


def main():
    false_negatives = []

    with open(DATASET, newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)

        for row in rows:
            expected = row["is_suspicious"] == "1"

            result = MessageAnalyzer.analyze(row["message_text"])

            if expected and not result.is_suspicious:
                false_negatives.append({
                    "id": row["message_id"],
                    "category": row["message_category"],
                    "message": row["message_text"],
                    "score": result.risk_score,
                    "reasons": result.reasons,
                })

    print("=" * 70)
    print("FALSE NEGATIVE ANALYSIS")
    print("=" * 70)
    print("Total false negatives:", len(false_negatives))

    for item in false_negatives:
        print()
        print("ID       :", item["id"])
        print("Category :", item["category"])
        print("Message  :", item["message"])
        print("Score    :", item["score"])
        print("Reasons  :", item["reasons"])


if __name__ == "__main__":
    main()