import csv

from risk_engine import RiskEngine


DATASET = "dataset/risk_evaluation_dataset.csv"


def to_bool(value):
    return value.lower() == "true"


def main():
    total = 0
    passed = 0

    with open(DATASET, newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)

        for row in rows:
            total += 1

            result = RiskEngine.assess(
                new_receiver=to_bool(row["new_receiver"]),
                suspicious_message=to_bool(
                    row["suspicious_message"]
                ),
                suspicious_payment_identifier=to_bool(
                    row["suspicious_payment_identifier"]
                ),
                location_changed=to_bool(
                    row["location_changed"]
                ),
                network_changed=to_bool(
                    row["network_changed"]
                ),
                new_device=to_bool(
                    row["new_device"]
                ),
                failed_authentication_attempts=int(
                    row["failed_authentication_attempts"]
                ),
                previous_suspicious_activity=to_bool(
                    row["previous_suspicious_activity"]
                ),
                receiver_reports=int(
                    row["receiver_reports"]
                ),
                unusual_payment_instruction=to_bool(
                    row["unusual_payment_instruction"]
                ),
            )

            expected = row["initial_risk"]

            if result.risk_level == expected:
                passed += 1

    print("--------------------------------")
    print("QuantumPay Risk Engine Evaluation")
    print("--------------------------------")
    print("Total records :", total)
    print("Passed        :", passed)
    print("Failed        :", total - passed)

    if total > 0:
        agreement = (passed / total) * 100
        print(f"Agreement     : {agreement:.2f}%")

    print("--------------------------------")


if __name__ == "__main__":
    main()