import hashlib


def canonical_transaction_string(
    transaction_id: int,
    sender: str,
    receiver: str,
    amount: float,
    transaction_type: str,
    timestamp: str,
) -> str:

    return (
        f"{transaction_id}|"
        f"{sender}|"
        f"{receiver}|"
        f"{amount:.2f}|"
        f"{transaction_type}|"
        f"{timestamp}"
    )


def sha3_256_hex(data: str) -> str:
    return hashlib.sha3_256(
        data.encode("utf-8")
    ).hexdigest()


def transaction_hash(
    transaction_id: int,
    sender: str,
    receiver: str,
    amount: float,
    transaction_type: str,
    timestamp: str,
) -> str:

    canonical_data = canonical_transaction_string(
        transaction_id=transaction_id,
        sender=sender,
        receiver=receiver,
        amount=amount,
        transaction_type=transaction_type,
        timestamp=timestamp,
    )

    return sha3_256_hex(canonical_data)