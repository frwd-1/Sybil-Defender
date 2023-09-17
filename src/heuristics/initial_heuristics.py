async def apply_initial_heuristics(transaction_event):
    # Check if there's a sender and receiver
    if not transaction_event.from_ or not transaction_event.to:
        return False

    if not transaction_event.transaction.value > 0:
        return False

    return True
