class MessageAnalyzer:
    HIGH_RISK_THRESHOLD = 3

    @staticmethod
    def analyze(message: str):
        text = (message or "").lower().strip()
        score = 0
        reasons = []

        if any(p in text for p in ["double your money", "guaranteed returns", "guaranteed profit", "high-return investment", "high return investment", "investment opportunity", "invest today"]):
            score += 3; reasons.append("Investment Scam")

        if any(p in text for p in ["you have won", "won a prize", "selected for a reward", "you are selected", "claim your reward", "claim it immediately"]):
            score += 3; reasons.append("Prize Or Reward Scam")

        if "refund" in text and any(p in text for p in ["send", "payment", "pay", "transfer", "verification", "payment link"]):
            score += 3; reasons.append("Refund Scam")

        if any(p in text for p in ["scan this qr code", "scan the qr code", "scan qr", "scan the qr"]):
            score += 3; reasons.append("QR Payment Instruction")

        if any(p in text for p in ["send money", "send payment", "send the payment", "make a payment", "transfer money", "transfer the requested amount", "payment required", "small payment"]):
            score += 2; reasons.append("Payment Request")

        if (any(p in text for p in ["payment", "transfer", "send"]) and any(p in text for p in ["verification", "verify", "confirm your account"])):
            score += 2; reasons.append("Payment Verification Pattern")

        if (any(p in text for p in ["urgent", "immediately", "now", "right away"]) and any(p in text for p in ["verify", "verification"])):
            score += 2; reasons.append("Urgent Verification")

        if any(p in text for p in ["account will be suspended", "account will be blocked", "account will be closed", "account has been suspended", "account has been blocked"]):
            score += 3; reasons.append("Account Threat")

        if ((any(p in text for p in ["account", "service"]) and any(p in text for p in ["suspended", "blocked", "stopped", "closed"]) and any(p in text for p in ["verify", "verification"]))):
            score += 2; reasons.append("Threat Based Verification")

        if any(p in text for p in ["click this link", "click the link", "open this link", "visit this link", "payment link", "provided link"]):
            score += 2; reasons.append("Suspicious Link")

        if any(p in text for p in ["share your otp", "send your otp", "tell me the otp", "provide your otp"]):
            score += 3; reasons.append("OTP Request")

        if any(p in text for p in ["urgent", "immediately", "act now", "right away", "within 24 hours"]):
            score += 1; reasons.append("Urgent Language")

        if any(p in text for p in ["verify your account", "verify your identity", "complete the verification", "verification required", "verify immediately"]):
            score += 1; reasons.append("Verification Request")

        return {"is_suspicious": score >= MessageAnalyzer.HIGH_RISK_THRESHOLD, "score": score, "reasons": reasons}
