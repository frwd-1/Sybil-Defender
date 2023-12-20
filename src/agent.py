import asyncio
import debugpy

from forta_agent import TransactionEvent

from src.hydra.database_controllers.db_controller import initialize_database

from src.hydra.database_controllers.db_controller import get_async_session
from src.hydra.database_controllers.db_utils import (
    add_transactions_b_to_db,
    remove_processed_transfers,
    remove_processed_contract_transactions,
)

from src.hydra.process.process import process_transactions
from src.hydra.heuristics.initial_heuristics import apply_initial_heuristics
from src.hydra.utils import globals
from src.constants import N, B_SIZE
from src.hydra.utils.utils import update_transaction_counter


transaction_b = []

# debugpy.listen(5678)
# armor
# check


def handle_transaction(transaction_event: TransactionEvent):
    print("running handle transaction")
    loop = asyncio.get_event_loop()
    network_name = transaction_event.network.name

    if not loop.is_running():
        loop.run_until_complete(initialize_database(network_name))
    else:
        loop.create_task(initialize_database(network_name))

    return loop.run_until_complete(
        handle_transaction_async(transaction_event, network_name)
    )


async def handle_transaction_async(
    transaction_event: TransactionEvent, network_name: str
):
    findings = []

    print("applying initial heuristics")
    # Assume apply_initial_heuristics is defined elsewhere
    if not await apply_initial_heuristics(transaction_event):
        return []

    transaction_b.append(transaction_event)
    print("batch size is:", len(transaction_b))
    if len(transaction_b) >= B_SIZE:
        async with get_async_session(network_name) as session:
            try:
                await add_transactions_b_to_db(session, transaction_b)
                print(f"{B_SIZE} transactions committed to the database")
            except Exception as e:
                print(f"An error occurred: {e}")

        transaction_b.clear()

    update_transaction_counter()

    print("transaction counter is", globals.transaction_counter)
    print("current block is...", transaction_event.block_number)
    if globals.transaction_counter >= N:
        print("processing transactions")
        findings.extend(await process_transactions(network_name))

        await remove_processed_transfers(network_name)
        await remove_processed_contract_transactions(network_name)

        globals.transaction_counter = 0
        print("ALL COMPLETE")
        return findings

    return []
