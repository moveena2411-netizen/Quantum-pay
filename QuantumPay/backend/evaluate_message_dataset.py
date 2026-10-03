import csv
from message_analyzer import MessageAnalyzer


DATASET_FILE = "dataset/message_dataset.csv"


def main():
    total = 0
    correct = 0
    false_positives = 0
    false_negatives = 0

    with open(DATASET_FILE, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            message = row["message_text"]

            # Dataset uses:
            # 0 = Normal
            # 1 = Suspicious
            expected = row["is_suspicious"].strip() == "1"

            result = MessageAnalyzer.analyze(message)

            predicted = result["is_suspicious"]

            total += 1

            if predicted == expected:
                correct += 1
            elif predicted and not expected:
                false_positives += 1
            elif not predicted and expected:
                false_negatives += 1

    incorrect = total - correct
    accuracy = (correct / total) * 100 if total else 0

    print()
    print("QuantumPay Message Analyzer Evaluation")
    print("---------------------------------------")
    print(f"Total records   : {total}")
    print(f"Correct         : {correct}")
    print(f"Incorrect       : {incorrect}")
    print(f"False positives : {false_positives}")
    print(f"False negatives : {false_negatives}")
    print(f"Accuracy        : {accuracy:.2f}%")
    print()


if __name__ == "__main__":
    main()