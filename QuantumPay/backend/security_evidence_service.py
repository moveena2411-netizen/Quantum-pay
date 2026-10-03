from sqlalchemy.orm import Session

import security_evidence


class SecurityEvidenceService:

    @staticmethod
    def check_identifier(
        db: Session,
        identifier: str
    ) -> dict:

        value = identifier.strip().lower()

        records = (
            db.query(security_evidence.SecurityEvidence)
            .filter(
                security_evidence.SecurityEvidence.identifier == value,
                security_evidence.SecurityEvidence.is_suspicious == True
            )
            .all()
        )

        if records:
            reasons = [
                record.reason
                for record in records
                if record.reason
            ]

            return {
                "is_suspicious": True,
                "evidence_count": len(records),
                "reasons": reasons,
            }

        return {
            "is_suspicious": False,
            "evidence_count": 0,
            "reasons": [],
        }