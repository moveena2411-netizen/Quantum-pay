# QuantumPay final implementation architecture

## Source basis
This bundle follows the first-review write-up: initial Risk Engine = LOW/HIGH; HIGH -> Challenge Engine; Challenge Engine = MEDIUM/HIGH; LOW uses Payment PIN + SHA3-256; final MEDIUM uses Payment PIN + SHA3-256 + ML-DSA-65; final HIGH is blocked. Transaction amount is transaction data, not a Risk Engine condition.

## Incoming security messages
The Message Analyzer processes simulated incoming security messages only. It extracts phone identifiers and stores suspicious identifiers in SecurityEvidence. The optional Send Money message is transaction information and is never passed to MessageAnalyzer and never changes risk.

## Trusted receiver rule
Stored evidence is a signal about an identifier, not a declaration that a person is malicious. A new receiver with stored security evidence can become HIGH. A receiver with previous successful transaction history does not become HIGH from that evidence alone. Other contextual signals can still cause HIGH.

## LOW
LOW -> Payment PIN -> create canonical transaction data -> SHA3-256 -> store integrity record -> authorize. No ML-DSA.

## HIGH -> Challenge
Initial HIGH -> create pending transaction -> contextual questions -> analyze answers. No money moves while the challenge is pending.

## MEDIUM
Final MEDIUM -> Payment PIN -> transfer -> canonical transaction -> SHA3-256 -> ML-DSA-65 sign -> ML-DSA-65 verify -> store signature -> commit.

## HIGH after challenge
Final HIGH -> BLOCKED. ML-DSA cannot override the block.

## Evaluation
The four 500-row datasets are synthetic deterministic evaluation sets. Their reported accuracy measures implementation consistency against the generated expected labels; it must not be presented as real-world fraud-detection accuracy.
