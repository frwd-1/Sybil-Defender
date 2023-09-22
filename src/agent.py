import asyncio
import matplotlib.pyplot as plt
from forta_agent import TransactionEvent
import decimal
from src.utils import (
    shed_oldest_Transfers,
    shed_oldest_ContractTransactions,
    extract_function_calls,
)
from src.constants import N, COMMUNITY_SIZE
from src.heuristics.advanced_heuristics import sybil_heuristics
from src.analysis.cluster_analysis import analyze_suspicious_clusters
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.database.models import (
    create_tables,
    transactions,
    Transfer,
    ContractTransaction,
)
from collections import defaultdict
from sqlalchemy.future import select

# TODO: remove redundant imports
from networkx import Graph
import networkx as nx
from community import best_partition  # For the Louvain method
from src.helpers import (
    process_community_using_jaccard_dbscan,
)
from src.database.controller import get_async_session
import numpy as np

transaction_counter = 0
database_initialized = False


# TODO: make final graph a global variable, window graph should merge into final graph
def handle_transaction(transaction_event: TransactionEvent):
    global database_initialized
    # TODO: refactor this initialization, doesn't have to initialize each time
    if not database_initialized:
        print("creating tables")
        asyncio.get_event_loop().run_until_complete(create_tables())
        database_initialized = True

    return asyncio.get_event_loop().run_until_complete(
        handle_transaction_async(transaction_event)
    )


async def handle_transaction_async(transaction_event: TransactionEvent):
    global transaction_counter
    findings = []

    print("applying initial heuristics")
    if not await apply_initial_heuristics(transaction_event):
        return []

    tx_hash = transaction_event.hash
    sender = transaction_event.from_
    receiver = transaction_event.to
    amount = transaction_event.transaction.value
    gas_price = transaction_event.gas_price
    timestamp = transaction_event.timestamp
    data = transaction_event.transaction.data

    print("transaction parameters set")

    async with get_async_session() as session:
        # Add sender and receiver to transactions table (repetitive part extracted)
        session.add(transactions(address=sender))
        print("added sender to transactions table")
        session.add(transactions(address=receiver))
        print("added receiver to transactions table")

        if transaction_event.transaction.data != "0x":
            session.add(
                ContractTransaction(
                    tx_hash=tx_hash,
                    sender=sender,
                    contract_address=receiver,
                    amount=amount,
                    timestamp=timestamp,
                    data=data,
                )
            )
            print("added ContractTransaction to ContractTransaction table")
        else:
            session.add(
                Transfer(
                    tx_hash=tx_hash,
                    sender=sender,
                    receiver=receiver,
                    amount=amount,
                    gas_price=gas_price,
                    timestamp=timestamp,
                )
            )
            print("added Transfer to Transfer table")

        await session.commit()
        print("data committed to table")

        transaction_counter += 1
        print("transaction counter is", transaction_counter)
    if transaction_counter >= N:
        print("processing clusters")

        findings = await process_transactions()
        await shed_oldest_Transfers()
        await shed_oldest_ContractTransactions()
        transaction_counter = 0
        print("ALL COMPLETE")
        return findings

    return []  # Returns an empty list if the threshold hasn't been reached


# TODO: initialize the existing graph with incoming_graph_data
async def process_transactions():
    G1 = Graph()

    print("graph created")

    async with get_async_session() as session:
        print("querying transactions")
        result = await session.execute(select(Transfer))
        transfers = result.scalars().all()

    # Create initial graph with all transfers
    for transfer in transfers:
        G1.add_edge(
            transfer.sender,
            transfer.receiver,
            timestamp=transfer.timestamp,
            gas_price=transfer.gas_price,
            amount=transfer.amount,
        )
    # TODO: CHeck loGIC??
    # Update edge weights based on variance
    # TODO: place edge weight logic in heuristic module
    edge_weights = defaultdict(int)

    for transfer in transfers:
        edge = (transfer.sender, transfer.receiver)
        edge_weights[edge] += 1

    processed_edges = set()

    for node in G1.nodes():
        for primary_edge in G1.edges(node, data=True):
            if (node, primary_edge[1]) in processed_edges or (
                primary_edge[1],
                node,
            ) in processed_edges:
                continue

            target = primary_edge[1]
            variances = []

            for adj_edge in G1.edges(target, data=True):
                gas_price_var = abs(
                    primary_edge[2]["gas_price"] - adj_edge[2]["gas_price"]
                )
                amount_var = abs(primary_edge[2]["amount"] - adj_edge[2]["amount"])
                timestamp_var = abs(
                    primary_edge[2]["timestamp"] - adj_edge[2]["timestamp"]
                )

                variances.append(gas_price_var + amount_var + timestamp_var)

            # Take mean variance for primary edge
            mean_variance = sum(variances) / len(variances) if variances else 0

            # Adjust the weight
            initial_weight = edge_weights[(node, target)]
            adjusted_weight = (1 / (mean_variance + 1)) * initial_weight

            # Update the edge in the graph
            G1.add_edge(node, target, weight=adjusted_weight)
            processed_edges.add((node, target))

    print("edges added to graph")

    # need to convert data from decimal to float for louvain
    for _, data in G1.nodes(data=True):
        for key, value in data.items():
            if isinstance(value, decimal.Decimal):
                data[key] = float(value)

    for _, _, data in G1.edges(data=True):
        for key, value in data.items():
            if isinstance(value, decimal.Decimal):
                data[key] = float(value)

    # Run louvain detection
    partitions_louvain = best_partition(G1)
    print("louvain partition created")

    # Assign each node its community
    for node, community in partitions_louvain.items():
        G1.nodes[node]["community"] = community

    to_remove = [
        node
        for node, community in partitions_louvain.items()
        if list(partitions_louvain.values()).count(community) < COMMUNITY_SIZE
    ]
    G1.remove_nodes_from(to_remove)

    # colors = [
    #     plt.cm.jet(
    #         np.linspace(0, 1, len(set(partitions_louvain.values())))[
    #             G1.nodes[node]["community"]
    #         ]
    #     )
    #     for node in G1.nodes()
    # ]

    # Draw the graph
    # nx.draw_spring(G1, with_labels=True, node_color=colors, cmap=plt.cm.jet)

    # plt.title("Louvain Community Detection")
    # plt.show()

    # # create graph file
    # nx.write_graphml(G1, "G1_graph_output.graphml")
    # print("graph output created")

    # final_partitions = dict(partitions_louvain)  # Initialize final_partitions
    # print("initialized final partition dictionary")

    # set communities to a dictionary
    grouped_addresses = defaultdict(set)
    for node, data in G1.nodes(data=True):
        community_id = data["community"]
        grouped_addresses[community_id].add(node)

    print(grouped_addresses)

    final_graph = nx.Graph()

    print("iterating through communities")
    async with get_async_session() as session:
        for community_id, addresses in grouped_addresses.items():
            result2 = await session.execute(
                select(ContractTransaction).where(
                    ContractTransaction.sender.in_(addresses)
                )
            )
            contract_transactions = result2.scalars().all()

            # organizes transaction data by the sender's address
            transactions_dict = {address: [] for address in addresses}
            for transaction in contract_transactions:
                function_calls = extract_function_calls(transaction.data)
                transactions_dict[transaction.sender].extend(function_calls)

            refined_clusters = await process_community_using_jaccard_dbscan(
                transactions_dict
            )

            # If refined clusters are found within the community, add the community to the final_graph
            if refined_clusters:
                for node in addresses:
                    final_graph.add_node(node, **G1.nodes[node])
                    for neighbor in G1[node]:
                        if (node, neighbor) not in final_graph.edges:
                            final_graph.add_edge(node, neighbor, **G1[node][neighbor])

                for transaction in contract_transactions:
                    if transaction.sender in final_graph.nodes:
                        final_graph.add_edge(
                            transaction.sender,
                            transaction.contract_address,
                            weight=int(transaction.amount),
                        )
                for address, cluster_id in refined_clusters.items():
                    if address in final_graph.nodes:
                        final_graph.nodes[address][
                            "refined_cluster"
                        ] = f"{community_id}_{cluster_id}"

    nx.write_graphml(final_graph, "FINAL_GRAPH_graph_output.graphml")

    print("running heuristics")
    refinedGraph = await sybil_heuristics(final_graph)
    print("analyzing suspicious clusters")
    print(refinedGraph)
    findings = analyze_suspicious_clusters(refinedGraph) or []

    print("COMPLETE")
    return findings


# TODO: implement active monitoring of identified sybil clusters aside from sliding window
# TODO: sliding window is designed to detect brand new sybils
# TODO: separate analysis structure that takes new transactions and analyzes them in terms of whether or not they are part of previously identified sybils
