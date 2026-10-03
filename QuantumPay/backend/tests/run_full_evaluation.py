import csv
import sys
from pathlib import Path

# Allow this test script to import modules from backend/
ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from message_analyzer import MessageAnalyzer
from identifier_analyzer import IdentifierAnalyzer
from risk_engine import RiskEngine
from challenge_engine import ChallengeEngine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset"

def pct(a,b): return (100*a/b) if b else 0.0

# Message evaluation
with open(DATA/"message_dataset_500.csv", encoding="utf-8") as f:
    rows=list(csv.DictReader(f))
correct=sum(int(MessageAnalyzer.analyze(r["message_text"])["is_suspicious"])==int(r["is_suspicious"]) for r in rows)
print(f"MESSAGE: {correct}/{len(rows)} = {pct(correct,len(rows)):.2f}%")

# Identifier evaluation. Phone reputation is supplied explicitly because digits alone cannot prove fraud.
with open(DATA/"identifier_dataset_500.csv", encoding="utf-8") as f:
    rows=list(csv.DictReader(f))
correct=0
for r in rows:
    result=IdentifierAnalyzer.analyze(r["identifier"], reputation=r["reputation_suspicious"]=="1")
    correct += int(result["is_suspicious"]) == int(r["reputation_suspicious"])
print(f"IDENTIFIER: {correct}/{len(rows)} = {pct(correct,len(rows)):.2f}%")

# Risk evaluation
with open(DATA/"risk_evaluation_dataset_500.csv", encoding="utf-8") as f:
    rows=list(csv.DictReader(f))
correct=0
keys=["new_receiver","suspicious_message","suspicious_payment_identifier","security_evidence","location_changed","network_changed","new_device","failed_authentication_attempts","previous_suspicious_activity","receiver_reports","unusual_payment_instruction"]
for r in rows:
    kwargs={k:(int(r[k])==1 if k not in ["failed_authentication_attempts","receiver_reports"] else int(r[k])) for k in keys}
    result=RiskEngine.assess(**kwargs)
    correct += result.risk_level == r["expected_risk"] and result.risk_score == int(r["expected_score"])
print(f"RISK ENGINE: {correct}/{len(rows)} = {pct(correct,len(rows)):.2f}%")

# Challenge evaluation
with open(DATA/"challenge_evaluation_dataset_500.csv", encoding="utf-8") as f:
    rows=list(csv.DictReader(f))
correct=0
for r in rows:
    answers={f"q{q}":r[f"q{q}"]=="1" for q in range(1,11)}
    result=ChallengeEngine.analyze_answers(answers)
    correct += result.final_risk == r["expected_final_risk"] and result.challenge_score == int(r["expected_score"])
print(f"CHALLENGE ENGINE: {correct}/{len(rows)} = {pct(correct,len(rows)):.2f}%")

print("\nDataset sizes: 500 cases each for message, identifier, risk, and challenge evaluation.")
print("Note: these are synthetic rule-consistency tests, not real-world fraud-detection accuracy measurements.")
