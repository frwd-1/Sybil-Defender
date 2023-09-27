import asyncio
from forta_agent import TransactionEvent
import decimal
from src.database.db_utils import (
    shed_oldest_Transfers,
    shed_oldest_ContractTransactions,
    extract_method_id,
)
from src.utils.constants import (
    N,
    COMMUNITY_SIZE,
    SIMILARITY_THRESHOLD,
    INTERACTION_RATIO,
)
from src.heuristics.advanced_heuristics import sybil_heuristics
from src.alerts.cluster_alerts import analyze_suspicious_clusters
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.database.models import (
    Interactions,
    Transfer,
    ContractTransaction,
)
from src.utils import globals
from src.utils.utils import update_transaction_counter
from collections import defaultdict
from sqlalchemy.future import select
from src.database.db_utils import add_transaction_to_db

from networkx import Graph
import networkx as nx
from community import best_partition  # For the Louvain method
from src.analysis.helpers import jaccard_similarity, extract_activity_pairs
from src.database.db_controller import get_async_session, initialize_database


# TODO: make final graph a global variable, window graph should merge into final graph
def handle_transaction(transaction_event: TransactionEvent):
    initialize_database()
    return asyncio.get_event_loop().run_until_complete(
        handle_transaction_async(transaction_event)
    )


async def handle_transaction_async(transaction_event: TransactionEvent):
    findings = []

    print("applying initial heuristics")
    if not await apply_initial_heuristics(transaction_event):
        return []

    async with get_async_session() as session:
        await add_transaction_to_db(session, transaction_event)
        await session.commit()
        print("transaction data committed to table")

        update_transaction_counter()

    print("transaction counter is", globals.transaction_counter)
    if globals.transaction_counter >= N:
        print("processing clusters")
        findings = await process_transactions()
        await shed_oldest_Transfers()
        await shed_oldest_ContractTransactions()

        globals.transaction_counter = 0
        print("ALL COMPLETE")
        return findings

    return []


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

    # Find nodes that aren't in any community
    nodes_without_community = set(G1.nodes()) - set(partitions_louvain.keys())

    # removes communities that are smaller than the required COMMUNITY_SIZE
    to_remove = [
        node
        for node, community in partitions_louvain.items()
        if list(partitions_louvain.values()).count(community) < COMMUNITY_SIZE
    ]

    # Add nodes without community to the removal list
    to_remove.extend(nodes_without_community)

    G1.remove_nodes_from(to_remove)
    # This will store edges that need to be removed
    edges_to_remove = []

    # Iterate over all edges of the graph
    for u, v in G1.edges():
        # If nodes u and v belong to different communities, mark the edge for removal
        if G1.nodes[u]["community"] != G1.nodes[v]["community"]:
            edges_to_remove.append((u, v))

    # Remove the marked edges from the graph
    G1.remove_edges_from(edges_to_remove)

    nx.write_graphml(G1, "G1_graph_output3.graphml")

    # set communities to a dictionary
    grouped_addresses = defaultdict(set)
    for node, data in G1.nodes(data=True):
        community_id = data["community"]
        grouped_addresses[community_id].add(node)

    print(grouped_addresses)

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
                communities_to_remove.add(community_id)
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
            if avg_similarity >= SIMILARITY_THRESHOLD:
                print(f"Retaining community {community_id} in G1")

                # Add contract transaction edges to the G1
                for transaction in contract_transactions:
                    if transaction.sender in G1.nodes:
                        # Ensure the sender node has the correct community label
                        G1.nodes[transaction.sender]["community"] = community_id

                        # If the contract address isn't already a node in the graph, add it
                        if transaction.contract_address not in G1.nodes:
                            G1.add_node(
                                transaction.contract_address, community=community_id
                            )

                        # Add the edge between the sender and the contract address
                        G1.add_edge(
                            transaction.sender,
                            transaction.contract_address,
                            weight=int(transaction.amount),
                            community=community_id,  # Adding community info to the edge as well
                        )
            else:
                print(
                    f"Marking community {community_id} for removal due to low similarity"
                )
                communities_to_remove.add(community_id)

        # Remove nodes belonging to communities marked for removal
        nodes_to_remove = [
            node
            for node, data in G1.nodes(data=True)
            if data.get("community") in communities_to_remove
        ]
        print(
            f"Removing {len(communities_to_remove)} communities and {len(nodes_to_remove)} nodes from G1"
        )
        G1.remove_nodes_from(nodes_to_remove)

    # List of edges that connect nodes from different communities
    inter_community_edges = [
        (u, v)
        for u, v in G1.edges()
        if G1.nodes[u]["community"] != G1.nodes[v]["community"]
    ]

    # Remove inter-community edges
    G1.remove_edges_from(inter_community_edges)

    print(f"Removed {len(inter_community_edges)} inter-community edges from G1.")

    nx.write_graphml(G1, "FINAL_GRAPH_graph3_output.graphml")
    breakpoint()

    print("running heuristics")
    refinedGraph = await sybil_heuristics(G1)
    print("analyzing suspicious clusters")
    print(refinedGraph)
    findings = analyze_suspicious_clusters(refinedGraph) or []

    print("COMPLETE")
    return findings


# TODO: implement active monitoring of identified sybil clusters aside from sliding window
# TODO: sliding window is designed to detect brand new sybils
# TODO: separate analysis structure that takes new transactions and analyzes them in terms of whether or not they are part of previously identified sybils
