from dataclasses import dataclass

from sqlalchemy.orm import Session

import models


@dataclass
class RiskDecision:
    risk_level: str
    risk_score: int
    reasons: list[str]


class RiskEngine:
    """
    QuantumPay initial transaction Risk Engine.

    IMPORTANT PROJECT RULES
    -----------------------
    1. Transaction amount is NEVER used for risk scoring.
    2. A receiver that the sender has successfully paid before is trusted
       for this receiver-level decision. Receiver-linked suspicious-message
       evidence must not turn that frequent/trusted receiver into HIGH risk.
    3. A genuinely new receiver, suspicious incoming-message evidence, or a
       suspicious payment identifier can trigger the HIGH -> Challenge path.
    4. The initial Risk Engine returns only LOW or HIGH.
       ChallengeEngine later converts HIGH into MEDIUM or HIGH.
    """

    HIGH_RISK_THRESHOLD = 3

    # A single receiver-level trigger is enough to require contextual
    # challenge. This is intentional because the project defines a new
    # receiver / suspicious receiver signal as requiring additional context.
    WEIGHTS = {
        "new_receiver": 3,
        "suspicious_message": 3,
        "suspicious_payment_identifier": 3,
        "security_evidence": 3,
        "location_changed": 1,
        "network_changed": 1,
        "new_device": 1,
        "failed_authentication_attempts": 2,
        "previous_suspicious_activity": 2,
        "receiver_reports": 2,
        "unusual_payment_instruction": 2,
    }

    @staticmethod
    def is_new_receiver(
        db: Session,
        sender_email: str,
        receiver_email: str,
    ) -> bool:
        """Return True only when sender has no previous successful transfer to receiver."""
        previous = (
            db.query(models.Transaction)
            .filter(
                models.Transaction.sender == sender_email,
                models.Transaction.receiver == receiver_email,
            )
            .first()
        )
        return previous is None

    @classmethod
    def assess(
        cls,
        *,
        new_receiver: bool = False,
        suspicious_message: bool = False,
        suspicious_payment_identifier: bool = False,
        security_evidence: bool = False,
        location_changed: bool = False,
        network_changed: bool = False,
        new_device: bool = False,
        failed_authentication_attempts: int = 0,
        previous_suspicious_activity: bool = False,
        receiver_reports: int = 0,
        unusual_payment_instruction: bool = False,
    ) -> RiskDecision:
        score = 0
        reasons: list[str] = []

        if new_receiver:
            score += cls.WEIGHTS["new_receiver"]
            reasons.append("Receiver has no previous successful transaction history")

        if suspicious_message:
            score += cls.WEIGHTS["suspicious_message"]
            reasons.append("Receiver is associated with suspicious incoming-message evidence")

        if suspicious_payment_identifier:
            score += cls.WEIGHTS["suspicious_payment_identifier"]
            reasons.append("Payment identifier is associated with suspicious activity")

        if security_evidence:
            score += cls.WEIGHTS["security_evidence"]
            reasons.append("Stored security evidence exists for the receiver identifier")

        if location_changed:
            score += cls.WEIGHTS["location_changed"]
            reasons.append("Transaction originated from a changed location")

        if network_changed:
            score += cls.WEIGHTS["network_changed"]
            reasons.append("Transaction originated from a changed network")

        if new_device:
            score += cls.WEIGHTS["new_device"]
            reasons.append("Transaction originated from an unfamiliar device")

        if failed_authentication_attempts > 0:
            score += cls.WEIGHTS["failed_authentication_attempts"]
            reasons.append("Recent failed authentication attempts detected")

        if previous_suspicious_activity:
            score += cls.WEIGHTS["previous_suspicious_activity"]
            reasons.append("Previous suspicious activity exists")

        if receiver_reports > 0:
            score += cls.WEIGHTS["receiver_reports"]
            reasons.append("Receiver has previous security reports")

        if unusual_payment_instruction:
            score += cls.WEIGHTS["unusual_payment_instruction"]
            reasons.append("Unusual payment instruction detected")

        level = "HIGH" if score >= cls.HIGH_RISK_THRESHOLD else "LOW"
        return RiskDecision(
            risk_level=level,
            risk_score=score,
            reasons=reasons,
        )
