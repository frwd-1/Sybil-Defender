import asyncio
import matplotlib.pyplot as plt
from forta_agent import TransactionEvent
import decimal
from src.utils import (
    shed_oldest_Transfers,
    shed_oldest_ContractTransactions,
    extract_method_id,
)
from src.constants import N, COMMUNITY_SIZE, SIMILARITY_THRESHOLD, INTERACTION_RATIO
from src.heuristics.advanced_heuristics import sybil_heuristics
from src.alerts.cluster_alerts import analyze_suspicious_clusters
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.database.models import (
    create_tables,
    Interactions,
    Transfer,
    ContractTransaction,
)
from collections import defaultdict
from sqlalchemy.future import select

# TODO: remove redundant imports
from networkx import Graph
import networkx as nx
from community import best_partition  # For the Louvain method
from src.helpers import jaccard_similarity, extract_activity_pairs
from src.database.controller import get_async_session
import numpy as np
import pdb


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
        session.add(Interactions(address=sender))
        print("added sender to transactions table")
        session.add(Interactions(address=receiver))
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
    # TODO: add error handling
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

    nx.write_graphml(G1, "G1_graph_output.graphml")

    # set communities to a dictionary
    grouped_addresses = defaultdict(set)
    for node, data in G1.nodes(data=True):
        community_id = data["community"]
        grouped_addresses[community_id].add(node)

    print(grouped_addresses)

    final_graph = nx.Graph()
    communities_to_remove = set()

    print("analyzing jaccard similarity of communities")
    async with get_async_session() as session:
        for community_id, addresses in grouped_addresses.items():
            print(f"Processing community {community_id} with addresses: {addresses}")

            result2 = await session.execute(
                select(ContractTransaction)
                .where(ContractTransaction.sender.in_(addresses))
                .order_by(ContractTransaction.timestamp)
            )

            # TODO: continue / iterate the loop if most EOAs haven't interacted with contracts
            contract_transactions = result2.scalars().all()
            print(
                f"Retrieved {len(contract_transactions)} contract transactions for community {community_id}"
            )
            unique_senders = set(
                transaction.sender for transaction in contract_transactions
            )
            print("unique senders:", len(unique_senders))
            print("number of addresses:", len(addresses))

            # TODO: add additional filter to check if addresses are interacting with same contract
            # TODO: add these to heuristics module
            # Check if less than half of the addresses have a ContractTransaction
            if len(unique_senders) < len(addresses) * INTERACTION_RATIO:
                print(
                    f"Skipping community {community_id} as less than half of its addresses have a ContractTransaction"
                )
                continue

            # Organizes transaction data by the sender's address
            # Constructing the transactions dictionary
            contract_activity_dict = defaultdict(set)

            for transaction in contract_transactions:
                # Extract the method ID
                methodId = extract_method_id(transaction.data)

                # Create a tuple of the method ID and contract address
                activity = (methodId, transaction.contract_address)

                # Store only unique method-contract pairs per sender
                contract_activity_dict[transaction.sender].add(activity)

            print("Finished building contract activity dictionary")

            # For each contract, count the number of EOAs that interacted with it
            contract_interaction_counts = defaultdict(set)
            for sender, activities in contract_activity_dict.items():
                for activity in activities:
                    contract = activity[1]
                    contract_interaction_counts[contract].add(sender)

            total_similarity = 0
            total_weights = 0
            print("Computing similarities between addresses...")
            for addr1 in addresses:
                for addr2 in addresses:
                    if addr1 == addr2:
                        continue

                    activities1 = contract_activity_dict[addr1]
                    activities2 = contract_activity_dict[addr2]

                    similarity = await jaccard_similarity(activities1, activities2)
                    weight = len(activities1) + len(activities2)
                    print(
                        f"Weight between {addr1} and {addr2}: {weight}, similarity: {similarity}"
                    )

                    total_similarity += similarity * weight
                    total_weights += weight

            avg_similarity = (
                total_similarity / total_weights if total_weights > 0 else 0
            )
            print(f"Average similarity for community {community_id}: {avg_similarity}")
            print(f"Average similarity for community {community_id}: {avg_similarity}")

            if avg_similarity >= SIMILARITY_THRESHOLD:
                print(f"Retaining community {community_id} in final graph")
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
            else:
                print(
                    f"Marking community {community_id} for removal due to low similarity"
                )
                communities_to_remove.add(community_id)

    # Remove communities with low similarity
    nodes_to_remove = [
        node
        for node, data in final_graph.nodes(data=True)
        if data["community"] in communities_to_remove
    ]
    print(f"Removing {len(nodes_to_remove)} nodes from final graph")
    final_graph.remove_nodes_from(nodes_to_remove)

    nx.write_graphml(final_graph, "FINAL_GRAPH_graph_output.graphml")
    pdb.set_trace()
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
