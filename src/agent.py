import networkx as nx
import asyncio
import debugpy
import json

from forta_agent import TransactionEvent
from sqlalchemy.future import select
from src.analysis.community_analysis.base_analyzer import (
    analyze_communities,
)
from src.database.db_controller import initialize_database
from src.analysis.transaction_analysis.algorithm import run_algorithm
from src.database.db_controller import get_async_session
from src.database.db_utils import (
    add_transactions_batch_to_db,
    remove_processed_transfers,
    remove_processed_contract_transactions,
)
from src.database.models import Transfer, ContractTransaction
from src.graph.graph_controller import (
    add_transactions_to_graph,
    adjust_edge_weights_and_variances,
    convert_decimal_to_float,
    process_partitions,
)
from src.dynamic.dynamic_communities import merge_new_communities
from src.dynamic.dynamic_suspicious import merge_final_graphs
from src.graph.final_graph_controller import load_graph, save_graph
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.utils import globals
from src.utils.constants import N
from src.utils.utils import update_transaction_counter
from src.database.clustering import write_graph_to_database

BATCH_SIZE = 500
transaction_batch = []

debugpy.listen(5678)
debugpy.wait_for_client()


def handle_transaction(transaction_event: TransactionEvent):
    print("running handle transaction")
    loop = asyncio.get_event_loop()

    if not loop.is_running():
        loop.run_until_complete(initialize_database())
    else:
        loop.create_task(initialize_database())

    return loop.run_until_complete(handle_transaction_async(transaction_event))


async def handle_transaction_async(transaction_event: TransactionEvent):
    findings = []
    await initialize_database()
    print("applying initial heuristics")
    if not await apply_initial_heuristics(transaction_event):
        return []

    transaction_batch.append(transaction_event)
    print("batch size is:", len(transaction_batch))
    if len(transaction_batch) >= BATCH_SIZE:
        async with get_async_session() as session:
            try:
                await add_transactions_batch_to_db(session, transaction_batch)
                await session.commit()
                print(f"{BATCH_SIZE} transactions committed to the database")
            except Exception as e:
                await session.rollback()
                print(f"An error occurred: {e}")

        # Clear the batch
        transaction_batch.clear()

    update_transaction_counter()

    print("transaction counter is", globals.transaction_counter)
    print("current block is...", transaction_event.block_number)
    if globals.transaction_counter >= N:
        print("processing transactions")

        findings.extend(await process_transactions(transaction_event))
        await remove_processed_transfers()
        await remove_processed_contract_transactions()

        globals.transaction_counter = 0
        print("ALL COMPLETE")
        return findings

    return []


async def process_transactions(transaction_event: TransactionEvent):
    findings = []
    network_name = transaction_event.network.name

    async with get_async_session() as session:
        print("pulling all transfers...")
        transfer_result = await session.execute(
            select(Transfer).where(
                (Transfer.processed == False) & (Transfer.chainId == network_name)
            )
        )
        transfers = transfer_result.scalars().all()
        print("transfers pulled")
        print("Number of transfers:", len(transfers))

        contract_transaction_result = await session.execute(
            select(ContractTransaction).where(
                (ContractTransaction.processed == False)
                & (ContractTransaction.chainId == network_name)
            )
        )
        contract_transactions = contract_transaction_result.scalars().all()
        print("transfers pulled")
        print("Number of transfers:", len(transfers))

        subgraph = nx.DiGraph()
        subgraph, added_edges = add_transactions_to_graph(transfers, subgraph)
        print("added total edges:", len(added_edges))

        # globals.global_added_edges.extend(added_edges)
        # Create a new directed subgraph using only the edges added in the current iteration

        subgraph = adjust_edge_weights_and_variances(transfers, subgraph)

        subgraph = convert_decimal_to_float(subgraph)
        # nx.write_graphml(globals.G1, "src/graph/graphs/initial_global_graph.graphml")

        print(f"Number of nodes in subgraph: {subgraph.number_of_nodes()}")
        print(f"Number of edges in subgraph: {subgraph.number_of_edges()}")

        subgraph_partitions = run_algorithm(subgraph)

        updated_subgraph = process_partitions(subgraph_partitions, subgraph)
        nx.write_graphml(
            updated_subgraph,
            f"src/graph/graphs/updated_{network_name}_subgraph.graphml",
        )

        # print("is initial batch?", globals.is_initial_batch)
        # if not globals.is_initial_batch:
        #     merge_new_communities(
        #         updated_subgraph,
        #     )
        # else:
        #     globals.G2 = updated_subgraph.copy()

        print("analyzing clusters for suspicious activity")
        analyzed_subgraph = (
            await analyze_communities(updated_subgraph, contract_transactions) or []
        )

        try:
            final_graph = load_graph(
                f"src/graph/graphs_two/final_{network_name}_graph.graphml"
            )

        except Exception as e:
            final_graph = nx.Graph()

        final_graph = merge_final_graphs(analyzed_subgraph, final_graph)

        for node, data in final_graph.nodes(data=True):
            for key, value in list(data.items()):
                if isinstance(value, type):
                    data[key] = str(value)
                elif isinstance(value, list):
                    data[key] = json.dumps(value)

        for u, v, data in final_graph.edges(data=True):
            for key, value in list(data.items()):
                if isinstance(value, type):
                    data[key] = str(value)
                elif isinstance(value, list):
                    data[key] = json.dumps(value)

        save_graph(
            final_graph, f"src/graph/graphs_two/final_{network_name}_graph.graphml"
        )

        findings = await write_graph_to_database(final_graph)

        for transfer in transfers:
            transfer.processed = True
        for transaction in contract_transactions:
            transaction.processed = True
        await session.commit()

        # globals.global_added_edges = []

        print("COMPLETE")
        return findings


# TODO: enable async / continuous processing of new transactions
# TODO: manage "cross-community edges"

# TODO: 1. don't replace any existing communities with l, just see if you have new communities
# TODO: 2. don't remove nodes / edges, until you are dropping old transactions, then just drop anything not part of a community
# TODO: 3. run LPA on existing communities to detect new nodes / edges

# TODO: label community centroids?
# TODO: have database retain the transactions and contract txs only for nodes in Sybil Clusters
# TODO: upgrade to Neo4j?

# TODO: double check advanced heuristics
# print("running advanced heuristics")
# await sybil_heuristics(globals.G1)

# TODO: status for active and inactive communities, alerts for new communities detected
# TODO: if new activity comes in on accounts already identified as sybils, flag it. monitor sybils specifically as new transactions come in

# TODO: does db need initialization?
# TODO: fix transfer timestamp / other timestamps
