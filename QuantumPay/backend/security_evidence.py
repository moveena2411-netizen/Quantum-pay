from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

from database import Base


class SecurityEvidence(Base):
    __tablename__ = "security_evidence"

    id = Column(Integer, primary_key=True, index=True)

    identifier = Column(
        String(255),
        nullable=False,
        index=True
    )

    identifier_type = Column(
        String(30),
        nullable=False
    )

    source = Column(
        String(50),
        nullable=False
    )

    message_text = Column(
        Text,
        nullable=True
    )

    reason = Column(
        String(1000),
        nullable=True
    )

    is_suspicious = Column(
        Boolean,
        nullable=False,
        default=False
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )