import csv
from pathlib import Path
from database import SessionLocal
from security_evidence import SecurityEvidence

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"dataset"/"incoming_message_dataset_500.csv"
db=SessionLocal()
try:
    added=0
    with open(path,encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["is_suspicious"] != "1":
                continue
            target=row["message_text"]
            # This seed is for synthetic identifiers only; it does not target the project's registered users.
            identifier=str(8000000000+int(row["message_id"]))
            exists=(db.query(SecurityEvidence).filter(SecurityEvidence.identifier==identifier).first())
            if exists:
                continue
            db.add(SecurityEvidence(identifier=identifier, identifier_type="PHONE", source="synthetic_dataset", message_text=target, reason="Synthetic suspicious dataset evidence", is_suspicious=True))
            added+=1
    db.commit()
    print(f"Synthetic security evidence added: {added}")
finally:
    db.close()
