QuantumPay Adaptive Risk Update

Files:
- main.py
- challenge_engine.py

Architecture:
1. Trusted previously successful receiver:
   LOW -> Payment PIN -> SHA3-256 -> SUCCESS
   No challenge, no ML-DSA.

2. New/registered or unregistered receiver with NO suspicious evidence:
   MEDIUM -> 3 questions -> if safe -> Payment PIN -> SHA3-256 -> SUCCESS
   No ML-DSA.
   If 2 or more of the 3 answers are concerning, final HIGH -> BLOCKED.

3. New/registered or unregistered receiver with suspicious incoming-SMS evidence:
   HIGH -> 6 questions -> safe answers -> MEDIUM -> Payment PIN -> SHA3-256 -> ML-DSA-65 -> SUCCESS
   Risky answers -> HIGH -> BLOCKED.

Important:
- Outgoing Send Money message text is not analyzed.
- Suspicious SMS evidence is a live Risk Engine signal; a phone number is not permanently HIGH.
- Amount is not a Risk Engine condition.
- Existing old CHALLENGE_PENDING records are treated as the old high-risk 6-question flow for compatibility.
- Flutter Send Money screen does not need modification because it already renders the questions returned by the backend dynamically.

Install:
Replace backend/main.py and backend/challenge_engine.py with these files.
Do not replace the database.
Restart uvicorn.
Then test the four flows described in the project guidance.
