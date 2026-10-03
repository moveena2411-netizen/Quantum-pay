import csv
from identifier_analyzer import IdentifierAnalyzer


DATASET_FILE = "dataset/identifier_dataset.csv"


def main():
    rows = []

    with open(DATASET_FILE, "r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    # Simulated reputation/evidence store.
    # In the real system this will come from the database.
    suspicious_identifiers = {
        row["identifier"].strip().lower()
        for row in rows
        if row["is_suspicious"].strip() == "1"
    }

    total = 0
    correct = 0
    false_positives = 0
    false_negatives = 0

    for row in rows:
        identifier = row["identifier"]

        expected = row["is_suspicious"].strip() == "1"

        reputation = identifier.strip().lower() in suspicious_identifiers

        result = IdentifierAnalyzer.analyze(
            identifier,
            reputation=reputation
        )

        predicted = result["is_suspicious"]

        total += 1

        if predicted == expected:
            correct += 1
        elif predicted and not expected:
            false_positives += 1
        elif not predicted and expected:
            false_negatives += 1

    accuracy = (correct / total) * 100

    print()
    print("QuantumPay Identifier Analyzer Evaluation")
    print("------------------------------------------")
    print(f"Total records   : {total}")
    print(f"Correct         : {correct}")
    print(f"Incorrect       : {total - correct}")
    print(f"False positives : {false_positives}")
    print(f"False negatives : {false_negatives}")
    print(f"Accuracy        : {accuracy:.2f}%")
    print()


if __name__ == "__main__":
    main()