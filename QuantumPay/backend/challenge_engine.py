from dataclasses import dataclass


@dataclass
class ChallengeResult:
    final_risk: str
    challenge_score: int
    reasons: list[str]


class ChallengeEngine:
    """Adaptive contextual challenge engine for QuantumPay.

    CLEAN_NEW:
        New/unregistered receiver with no suspicious evidence.
        Uses 3 important questions. A safe result remains MEDIUM and
        the transaction uses Payment PIN + SHA3-256 only.

    HIGH_SUSPICIOUS:
        New/unregistered receiver associated with suspicious security
        evidence. Uses 6 questions. A safe result becomes MEDIUM and
        the transaction uses Payment PIN + SHA3-256 + ML-DSA-65.
        A risky result becomes HIGH and is blocked.
    """

    MODE_CLEAN_NEW = "CLEAN_NEW"
    MODE_HIGH_SUSPICIOUS = "HIGH_SUSPICIOUS"

    # Clean/new flow: two or more concerning answers -> HIGH/block.
    CLEAN_HIGH_THRESHOLD = 2

    # Suspicious flow: score 4 or more -> HIGH/block.
    HIGH_THRESHOLD = 4

    CLEAN_QUESTIONS = [
        {
            "id": "q1",
            "question": "Do you personally know or recognize the receiver?",
        },
        {
            "id": "q2",
            "question": "Do you understand the purpose of this payment?",
        },
        {
            "id": "q3",
            "question": "Have you independently verified the receiver using a trusted channel?",
        },
    ]

    HIGH_QUESTIONS = [
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
    ]

    @classmethod
    def get_questions(
        cls,
        risk_reasons: list[str] | None = None,
        mode: str = MODE_HIGH_SUSPICIOUS,
    ):
        if mode == cls.MODE_CLEAN_NEW:
            return cls.CLEAN_QUESTIONS
        return cls.HIGH_QUESTIONS

    @classmethod
    def analyze_answers(
        cls,
        answers: dict[str, bool],
        mode: str = MODE_HIGH_SUSPICIOUS,
    ) -> ChallengeResult:
        if mode == cls.MODE_CLEAN_NEW:
            return cls._analyze_clean_answers(answers)
        return cls._analyze_high_answers(answers)

    @classmethod
    def _analyze_clean_answers(cls, answers: dict[str, bool]) -> ChallengeResult:
        score = 0
        reasons = []

        if answers.get("q1") is False:
            score += 1
            reasons.append("Sender does not personally know or recognize the receiver")

        if answers.get("q2") is False:
            score += 1
            reasons.append("Sender does not understand the payment purpose")

        if answers.get("q3") is False:
            score += 1
            reasons.append("Receiver has not been independently verified")

        final_risk = "HIGH" if score >= cls.CLEAN_HIGH_THRESHOLD else "MEDIUM"
        return ChallengeResult(
            final_risk=final_risk,
            challenge_score=score,
            reasons=reasons,
        )

    @classmethod
    def _analyze_high_answers(cls, answers: dict[str, bool]) -> ChallengeResult:
        score = 0
        reasons = []

        if answers.get("q1") is False:
            score += 2
            reasons.append(
                "Sender indicates that they did not personally initiate the payment"
            )

        if answers.get("q2") is False:
            score += 1
            reasons.append("Sender does not recognize the receiver")

        if answers.get("q3") is False:
            score += 1
            reasons.append("Sender does not understand the payment purpose")

        if answers.get("q4") is True:
            score += 2
            reasons.append(
                "Sender reports being pressured or instructed to make the payment"
            )

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
