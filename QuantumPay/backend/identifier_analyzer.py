import csv
import re
from pathlib import Path


class IdentifierAnalyzer:
    """
    Runtime lookup for receiver identifiers.

    The identifier dataset is used at transaction time. It is not merely an
    offline evaluation dataset. The analyzer is deliberately tolerant of the
    column names used by the generated QuantumPay datasets.
    """

    DATASET_CANDIDATES = (
        "identifier_dataset_500.csv",
        "identifier_dataset.csv",
    )

    @classmethod
    def _dataset_path(cls) -> Path:
        backend_dir = Path(__file__).resolve().parent
        for name in cls.DATASET_CANDIDATES:
            path = backend_dir / "dataset" / name
            if path.exists():
                return path
        return backend_dir / "dataset" / cls.DATASET_CANDIDATES[0]

    @staticmethod
    def normalize_identifier(value: str) -> str:
        value = (value or "").strip()
        # Phone numbers are the primary runtime identifier in Send Money.
        digits = re.sub(r"\D", "", value)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 10 and digits[0] in "6789":
            return digits
        return value.lower()

    @classmethod
    def _row_identifier(cls, row: dict) -> str:
        for key in (
            "identifier",
            "phone",
            "phone_number",
            "sender_phone",
            "payment_identifier",
            "value",
        ):
            value = row.get(key)
            if value not in (None, ""):
                return cls.normalize_identifier(str(value))
        return ""

    @staticmethod
    def _row_suspicious(row: dict) -> bool:
        for key in (
            "is_suspicious",
            "suspicious",
            "label",
            "risk_label",
            "risk_level",
            "is_risky",
        ):
            if key not in row or row[key] in (None, ""):
                continue
            value = str(row[key]).strip().lower()
            if value in {"1", "true", "yes", "suspicious", "high", "medium", "risky", "fraud"}:
                return True
            if value in {"0", "false", "no", "normal", "low", "safe", "legitimate"}:
                return False
        return False

    @staticmethod
    def _row_reason(row: dict) -> str:
        for key in ("reason", "category", "message_category", "risk_reason", "description"):
            value = row.get(key)
            if value not in (None, ""):
                return str(value)
        return "Identifier matched the suspicious-identifier dataset"

    @classmethod
    def analyze(cls, identifier: str) -> dict:
        normalized = cls.normalize_identifier(identifier)
        path = cls._dataset_path()

        if not path.exists():
            return {
                "identifier": normalized,
                "found": False,
                "is_suspicious": False,
                "reason": "Identifier dataset not found",
                "dataset": str(path),
            }

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_identifier = cls._row_identifier(row)
                if row_identifier != normalized:
                    continue

                return {
                    "identifier": normalized,
                    "found": True,
                    "is_suspicious": cls._row_suspicious(row),
                    "reason": cls._row_reason(row),
                    "row": row,
                    "dataset": str(path),
                }

        return {
            "identifier": normalized,
            "found": False,
            "is_suspicious": False,
            "reason": "Identifier not present in dataset",
            "dataset": str(path),
        }
