from dataclasses import dataclass


@dataclass
class ChallengeResult:
    final_risk: str
    challenge_score: int
    reasons: list[str]


class ChallengeEngine:
    """Six-question contextual challenge for untrusted receivers."""

    HIGH_THRESHOLD = 4

    QUESTIONS = [
        {"id": "q1", "question": "Did you personally initiate this payment?"},
        {"id": "q2", "question": "Do you personally know or recognize the receiver?"},
        {"id": "q3", "question": "Do you understand the purpose of this payment?"},
        {"id": "q4", "question": "Did anyone ask, instruct, or pressure you to make this payment?"},
        {"id": "q5", "question": "Were you told to complete the payment immediately?"},
        {"id": "q6", "question": "Have you independently verified the receiver using a trusted channel?"},
    ]

    @classmethod
    def get_questions(cls, risk_reasons: list[str] | None = None):
        return cls.QUESTIONS

    @classmethod
    def analyze_answers(cls, answers: dict[str, bool]) -> ChallengeResult:
        score = 0
        reasons = []

        if answers.get("q1") is False:
            score += 2
            reasons.append("Sender indicates that they did not personally initiate the payment")

        if answers.get("q2") is False:
            score += 1
            reasons.append("Sender does not recognize the receiver")

        if answers.get("q3") is False:
            score += 1
            reasons.append("Sender does not understand the payment purpose")

        if answers.get("q4") is True:
            score += 2
            reasons.append("Sender reports being pressured or instructed to make the payment")

        if answers.get("q5") is True:
            score += 1
            reasons.append("Sender reports unusual urgency associated with the payment")

        if answers.get("q6") is False:
            score += 1
            reasons.append("Receiver has not been independently verified")

        final_risk = "HIGH" if score >= cls.HIGH_THRESHOLD else "MEDIUM"
        return ChallengeResult(
            final_risk=final_risk,
            challenge_score=score,
            reasons=reasons,
        )
