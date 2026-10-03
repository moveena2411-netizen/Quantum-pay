import re
from sqlalchemy.orm import Session

from message_analyzer import MessageAnalyzer
from security_evidence import SecurityEvidence


PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)")


class SecurityMessageService:
    """Processes incoming security messages, not outgoing payment messages."""

    @staticmethod
    def normalize_phone(value: str) -> str:
        value = re.sub(r"[^0-9+]", "", value.strip())
        if value.startswith("+91"):
            return value[3:]
        if value.startswith("91") and len(value) == 12:
            return value[2:]
        return value

    @classmethod
    def extract_phone_numbers(cls, text: str) -> list[str]:
        numbers = []
        for match in PHONE_PATTERN.findall(text or ""):
            normalized = cls.normalize_phone(match)
            if normalized and normalized not in numbers:
                numbers.append(normalized)
        return numbers

    @classmethod
    def receive_message(
        cls,
        db: Session,
        sender_phone: str,
        message_text: str,
        source: str = "incoming_sms",
    ):
        sender_phone = cls.normalize_phone(sender_phone)
        message_text = message_text.strip()

        if not sender_phone:
            raise ValueError("Sender phone number is required")
        if not message_text:
            raise ValueError("Message text is required")

        analysis = MessageAnalyzer.analyze(message_text)
        extracted_numbers = cls.extract_phone_numbers(message_text)

        stored_identifiers = []

        # The sender itself becomes security evidence when the message is suspicious.
        if analysis["is_suspicious"]:
            cls._store_evidence(
                db=db,
                identifier=sender_phone,
                message_text=message_text,
                reason="Incoming suspicious message: " + ", ".join(analysis["reasons"]),
                source=source,
            )
            stored_identifiers.append(sender_phone)

            # Any phone number contained inside the suspicious message is also
            # stored as a suspicious payment/security identifier.
            for number in extracted_numbers:
                if number == sender_phone:
                    continue
                cls._store_evidence(
                    db=db,
                    identifier=number,
                    message_text=message_text,
                    reason=(
                        "Phone number extracted from suspicious message: "
                        + ", ".join(analysis["reasons"])
                    ),
                    source="message_extracted_identifier",
                )
                stored_identifiers.append(number)

        db.commit()

        return {
            "sender_phone": sender_phone,
            "message": message_text,
            "is_suspicious": analysis["is_suspicious"],
            "score": analysis["score"],
            "reasons": analysis["reasons"],
            "extracted_phone_numbers": extracted_numbers,
            "stored_suspicious_identifiers": stored_identifiers,
        }

    @classmethod
    def analyze_shared_message(
        cls,
        db: Session,
        message_text: str,
        source: str = "shared_message",
    ):
        """Analyze text shared from another phone app.

        A shared message does not reliably provide the original SMS sender
        phone number, so only phone identifiers actually extracted from the
        message are stored as suspicious evidence.
        """
        message_text = (message_text or "").strip()

        if not message_text:
            raise ValueError("Message text is required")

        analysis = MessageAnalyzer.analyze(message_text)
        extracted_numbers = cls.extract_phone_numbers(message_text)
        stored_identifiers = []

        if analysis["is_suspicious"]:
            reason = (
                "Shared suspicious message: "
                + ", ".join(analysis["reasons"])
            )

            for number in extracted_numbers:
                cls._store_evidence(
                    db=db,
                    identifier=number,
                    message_text=message_text,
                    reason=(
                        "Phone number extracted from shared suspicious message: "
                        + ", ".join(analysis["reasons"])
                    ),
                    source="shared_message_identifier",
                )
                stored_identifiers.append(number)

            # If the suspicious shared message contains no phone number,
            # keep the analysis result but do not invent an identifier.
            if not extracted_numbers:
                cls._store_evidence(
                    db=db,
                    identifier="MESSAGE_ONLY",
                    message_text=message_text,
                    reason=reason,
                    source=source,
                )

        db.commit()

        return {
            "message": message_text,
            "is_suspicious": analysis["is_suspicious"],
            "score": analysis["score"],
            "reasons": analysis["reasons"],
            "extracted_phone_numbers": extracted_numbers,
            "stored_suspicious_identifiers": stored_identifiers,
            "source": source,
        }

    @staticmethod
    def _store_evidence(
        db: Session,
        identifier: str,
        message_text: str,
        reason: str,
        source: str,
    ):
        existing = (
            db.query(SecurityEvidence)
            .filter(
                SecurityEvidence.identifier == identifier,
                SecurityEvidence.message_text == message_text,
            )
            .first()
        )

        if existing:
            existing.is_suspicious = True
            existing.reason = reason
            existing.source = source
            return

        db.add(
            SecurityEvidence(
                identifier=identifier,
                identifier_type="PHONE",
                source=source,
                message_text=message_text,
                reason=reason,
                is_suspicious=True,
            )
        )
