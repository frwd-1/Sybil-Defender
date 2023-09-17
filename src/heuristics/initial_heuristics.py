async def apply_initial_heuristics(transaction_event):
    print("checking if sender or receiver")
    if not transaction_event.from_ or not transaction_event.to:
        print("false")
        return False
    print("checking if value is greater than 0")
    if not transaction_event.transaction.value > 0:
        print("false")
        return False
    print("true")
    return True
