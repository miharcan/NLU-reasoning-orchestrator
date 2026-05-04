from __future__ import annotations

from typing import Dict


def authenticate_user(user_id: str) -> Dict[str, str]:
    return {"status": "authenticated", "user_id": user_id}


def check_transaction(user_id: str, amount: float, date: str) -> Dict[str, str | float]:
    return {
        "status": "found",
        "user_id": user_id,
        "merchant": "Amazon",
        "amount": amount,
        "date": date,
        "transaction_id": "TXN-445122",
    }


def create_dispute_case(user_id: str, transaction_id: str) -> Dict[str, str]:
    return {
        "case_id": "CASE-10293",
        "status": "created",
        "user_id": user_id,
        "transaction_id": transaction_id,
    }


def update_card_on_file(user_id: str, card_last4: str) -> Dict[str, str]:
    return {
        "status": "updated",
        "user_id": user_id,
        "card_last4": card_last4,
    }
