from datetime import date

# Transaction reference counter
TRANSACTION_COUNTER = {"next_id": 5001}
BANK_ACCOUNTS_DB = {
    "0012345678": {
        "account_name": "John Doe",
        "account_type": "savings",
        "balance": 150000.50,
        "currency": "NGN",
        "status": "active",
        "bank_name": "Udara Bank",
        "linked_cards": [
            {"card_type": "debit", "card_last4": "1234", "expiry": "09/27", "status": "active"}
        ],
        "transactions": [
            {"id": 1001, "date": "2025-09-15", "type": "deposit", "amount": 50000, "description": "Salary Credit"},
            {"id": 1002, "date": "2025-09-20", "type": "withdrawal", "amount": 20000, "description": "ATM Withdrawal"},
            {"id": 1003, "date": "2025-09-28", "type": "transfer_out", "amount": 10000, "description": "Transfer to 0023456789"},
            {"id": 1004, "date": "2025-10-02", "type": "deposit", "amount": 30000, "description": "Transfer from 0034567890"}
        ],
        "beneficiaries": [
            {"name": "Jane Smith", "account_number": "0023456789", "bank_name": "GTBank"},
            {"name": "Michael Adams", "account_number": "0034567890", "bank_name": "UBA"}
        ]
    },
    "0023456789": {
        "account_name": "Jane Smith",
        "account_type": "current",
        "balance": 245000.00,
        "currency": "NGN",
        "status": "active",
        "bank_name": "GTBank",
        "linked_cards": [
            {"card_type": "credit", "card_last4": "6789", "expiry": "03/26", "status": "active"}
        ],
        "transactions": [
            {"id": 2001, "date": "2025-09-12", "type": "deposit", "amount": 100000, "description": "Freelance Payment"},
            {"id": 2002, "date": "2025-09-15", "type": "transfer_in", "amount": 10000, "description": "Transfer from 0012345678"},
            {"id": 2003, "date": "2025-10-01", "type": "bill_payment", "amount": 15000, "description": "DSTV Subscription"}
        ],
        "beneficiaries": [
            {"name": "John Doe", "account_number": "0012345678", "bank_name": "Udara Bank"},
            {"name": "Samuel Peters", "account_number": "0045678901", "bank_name": "Access Bank"}
        ]
    }
}

def get_account_info(account_number):
    """Retrieve detailed information about a specific bank account."""
    account = BANK_ACCOUNTS_DB.get(str(account_number))
    if not account:
        return {"error": f"Account '{account_number}' not found."}

    return {
        "account_number": account_number,
        "account_name": account["account_name"],
        "account_type": account["account_type"],
        "balance": account["balance"],
        "currency": account["currency"],
        "status": account["status"],
        "bank_name": account["bank_name"]
    }

def transfer_funds(from_account, to_account, amount, narration="Funds Transfer"):
    """Transfer funds between two accounts."""
    sender = BANK_ACCOUNTS_DB.get(str(from_account))
    receiver = BANK_ACCOUNTS_DB.get(str(to_account))

    if not sender:
        return {"error": f"Sender account '{from_account}' not found."}
    if not receiver:
        return {"error": f"Receiver account '{to_account}' not found."}
    if sender["status"] != "active":
        return {"error": f"Sender account '{from_account}' is not active."}
    if sender["balance"] < amount:
        return {"error": "Insufficient balance."}

    # Process transaction
    sender["balance"] -= amount
    receiver["balance"] += amount

    transaction_id = TRANSACTION_COUNTER["next_id"]
    TRANSACTION_COUNTER["next_id"] += 1

    transaction_entry_sender = {
        "id": transaction_id,
        "date": date.today().isoformat(),
        "type": "transfer_out",
        "amount": amount,
        "description": f"Transfer to {to_account} - {narration}"
    }

    transaction_entry_receiver = {
        "id": transaction_id,
        "date": date.today().isoformat(),
        "type": "transfer_in",
        "amount": amount,
        "description": f"Transfer from {from_account} - {narration}"
    }

    sender["transactions"].append(transaction_entry_sender)
    receiver["transactions"].append(transaction_entry_receiver)

    return {
        "transaction_id": transaction_id,
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount,
        "currency": sender["currency"],
        "message": f"₦{amount:,.2f} successfully transferred from {from_account} to {to_account}."
    }


def get_transaction_history(account_number, limit=5):
    """Retrieve recent transaction history for an account."""
    account = BANK_ACCOUNTS_DB.get(str(account_number))
    if not account:
        return {"error": f"Account '{account_number}' not found."}

    transactions = account["transactions"][-limit:]
    return {
        "account_number": account_number,
        "account_name": account["account_name"],
        "recent_transactions": transactions
    }

def add_beneficiary(account_number, beneficiary_name, beneficiary_account, beneficiary_bank):
    """Add a new beneficiary to a user's account."""
    account = BANK_ACCOUNTS_DB.get(str(account_number))
    if not account:
        return {"error": f"Account '{account_number}' not found."}

    for b in account["beneficiaries"]:
        if b["account_number"] == beneficiary_account:
            return {"error": f"Beneficiary '{beneficiary_account}' already exists."}

    new_beneficiary = {
        "name": beneficiary_name,
        "account_number": beneficiary_account,
        "bank_name": beneficiary_bank
    }

    account["beneficiaries"].append(new_beneficiary)
    return {
        "message": f"Beneficiary '{beneficiary_name}' added successfully.",
        "beneficiaries": account["beneficiaries"]
    }

def manage_card(account_number, card_last4, action):
    """Block or activate a debit/credit card."""
    account = BANK_ACCOUNTS_DB.get(str(account_number))
    if not account:
        return {"error": f"Account '{account_number}' not found."}

    for card in account["linked_cards"]:
        if card["card_last4"] == card_last4:
            if action == "block":
                card["status"] = "blocked"
                return {"message": f"Card ending with {card_last4} has been blocked."}
            elif action == "activate":
                card["status"] = "active"
                return {"message": f"Card ending with {card_last4} has been activated."}
            else:
                return {"error": "Invalid action. Use 'block' or 'activate'."}

    return {"error": f"Card ending with {card_last4} not found for account {account_number}."}

def pay_bill(account_number, biller_name, amount, bill_type, reference=None):
    """Pay a bill from the user's account."""
    account = BANK_ACCOUNTS_DB.get(str(account_number))
    if not account:
        return {"error": f"Account '{account_number}' not found."}
    if account["balance"] < amount:
        return {"error": "Insufficient balance to pay the bill."}

    account["balance"] -= amount
    transaction_id = TRANSACTION_COUNTER["next_id"]
    TRANSACTION_COUNTER["next_id"] += 1

    transaction_entry = {
        "id": transaction_id,
        "date": "2025-10-06",
        "type": "bill_payment",
        "amount": amount,
        "description": f"{bill_type.title()} bill to {biller_name} (Ref: {reference})"
    }
    account["transactions"].append(transaction_entry)

    return {
        "transaction_id": transaction_id,
        "message": f"₦{amount:,.2f} {bill_type} bill payment to {biller_name} completed successfully.",
        "remaining_balance": account["balance"]
    }



# Function mapping dictionary
FUNCTION_MAP = {
    "get_account_info": get_account_info,
    "transfer_funds": transfer_funds,
    "get_transaction_history": get_transaction_history,
    "add_beneficiary": add_beneficiary,
    "manage_card": manage_card,
    "pay_bill": pay_bill
}
