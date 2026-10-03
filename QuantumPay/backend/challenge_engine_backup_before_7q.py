from dataclasses import dataclass


@dataclass
class ChallengeResult:
    final_risk: str
    challenge_score: int
    reasons: list[str]


class ChallengeEngine:
    """Contextual challenge for untrusted/new receivers.

    The questions collect contextual evidence only. They never request
    passwords, PINs, OTPs, or passkey secrets.
    """

    HIGH_THRESHOLD = 4

    # Exactly 7 questions as requested for the final project.
    QUESTIONS = [
        {
            "id": "q1",
            "question": "Did you personally initiate this payment?",
        },
        {
            "id": "q2",
            "question": "Do you personally know or recognize the receiver?",
        },
        {
            "id": "q3",
            "question": "Do you understand the purpose of this payment?",
        },
        {
            "id": "q4",
            "question": "Did anyone ask, instruct, or pressure you to make this payment?",
        },
        {
            "id": "q5",
            "question": "Were you told to complete the payment immediately?",
        },
        {
            "id": "q6",
            "question": "Have you independently verified the receiver using a trusted channel?",
        },
        {
            "id": "q7",
            "question": "Were you asked to scan a QR code or use a payment link provided by someone else?",
        },
    ]

    @classmethod
    def get_questions(cls, risk_reasons: list[str] | None = None):
        return cls.QUESTIONS

    @classmethod
    def analyze_answers(cls, answers: dict[str, bool]) -> ChallengeResult:
        score = 0
        reasons: list[str] = []

        # Q1: user did not personally initiate payment
        if answers.get("q1") is False:
            score += 2
            reasons.append(
                "Sender indicates that they did not personally initiate the payment"
            )

        # Q2: receiver is not recognized
        if answers.get("q2") is False:
            score += 1
            reasons.append("Sender does not recognize the receiver")

        # Q3: purpose is unclear
        if answers.get("q3") is False:
            score += 1
            reasons.append(
                "Sender does not clearly understand the purpose of the payment"
            )

        # Q4: pressure/instruction is a strong contextual signal
        if answers.get("q4") is True:
            score += 2
            reasons.append(
                "Sender reports being pressured or instructed to make the payment"
            )

        # Q5: unusual urgency
        if answers.get("q5") is True:
            score += 1
            reasons.append("Sender reports unusual urgency associated with the payment")

        # Q6: receiver not independently verified
        if answers.get("q6") is False:
            score += 1
            reasons.append("Receiver has not been independently verified")

        # Q7: external QR/payment link
        if answers.get("q7") is True:
            score += 1
            reasons.append(
                "Sender reports an externally provided QR code or payment link"
            )

        final_risk = "HIGH" if score >= cls.HIGH_THRESHOLD else "MEDIUM"

        return ChallengeResult(
            final_risk=final_risk,
            challenge_score=score,
            reasons=reasons,
        )
