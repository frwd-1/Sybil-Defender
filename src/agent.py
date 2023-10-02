import networkx as nx
import igraph as ig
import collections
import asyncio

from forta_agent import TransactionEvent
from community import best_partition  # For the Louvain method
from sqlalchemy.future import select
from src.alerts.cluster_alerts import analyze_suspicious_clusters
from src.analysis.community_analyzer import (
    group_addresses_by_community,
    analyze_communities,
)
from src.analysis.louvain import run_louvain_algorithm
from src.database.db_controller import get_async_session, initialize_database
from src.database.db_utils import (
    add_transaction_to_db,
    shed_oldest_Transfers,
    shed_oldest_ContractTransactions,
    store_graph_clusters,
)
from src.database.models import Transfer
from src.graph.graph_controller import (
    add_transactions_to_graph,
    adjust_edge_weights_and_variances,
    convert_decimal_to_float,
    remove_communities_and_nodes,
    remove_inter_community_edges,
)
from src.heuristics.advanced_heuristics import sybil_heuristics
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.utils import globals
from src.utils.constants import N, COMMUNITY_SIZE
from src.utils.utils import update_transaction_counter


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
        try:
            await add_transaction_to_db(session, transaction_event)
            await session.commit()
            print("transaction data committed to table")
        except Exception as e:
            print(f"Error committing transaction to database: {e}")
            session.rollback()  # Rollback the transaction if there's an error

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
    # TODO: add error handling
    async with get_async_session() as session:
        print("querying transactions")
        result = await session.execute(select(Transfer))
        transfers = result.scalars().all()

    # Create initial graph with all transfers
    add_transactions_to_graph(transfers)

    # set edge weights for graph
    adjust_edge_weights_and_variances(transfers)

    # need to convert data from decimal to float for louvain
    convert_decimal_to_float()

    partitions = run_louvain_algorithm(globals.G1)

    # Filter out small communities
    filtered_partitions = {}
    for node, community in partitions.items():
        # Get all nodes assigned to the current community
        community_nodes = [n for n, c in partitions.items() if c == community]

        # Only keep communities larger than threshold
        if len(community_nodes) >= COMMUNITY_SIZE:
            filtered_partitions[node] = community

    # Assign filtered communities back to nodes in the graph
    for node, community in filtered_partitions.items():
        globals.G1.nodes[node]["community"] = community

    # # Assign each node its community

    # for node, community in partitions.items():
    #     globals.G1.nodes[node]["community"] = community

    # Debugging: Print the total number of nodes in SCC communities after assignment
    # scc_nodes = [
    #     node
    #     for node, data in globals.G1.nodes(data=True)
    #     if "SCC" in data.get("community", "")
    # ]
    # print(f"Total Number of Nodes Assigned to SCCs: {len(scc_nodes)}")
    # wcc_nodes = [
    #     node
    #     for node, data in globals.G1.nodes(data=True)
    #     if "WCC" in data.get("community", "")
    # ]

    # print(f"SCC nodes count after assignment: {len(scc_nodes)}")
    # print(f"WCC nodes count after assignment: {len(wcc_nodes)}")

    # Find nodes that aren't in any community
    nodes_without_community = set(globals.G1.nodes()) - set(partitions.keys())

    to_remove = set()
    community_counts = collections.Counter(partitions.values())
    for community, count in community_counts.items():
        if count < COMMUNITY_SIZE:
            # Adding all nodes belonging to this community to to_remove
            to_remove.update(
                node
                for node, assigned_community in partitions.items()
                if assigned_community == community
            )

    # Add nodes without community to the removal list
    to_remove.update(nodes_without_community)

    globals.G1.remove_nodes_from(to_remove)
    # This will store edges that need to be removed
    edges_to_remove = []

    # Iterate over all edges of the graph
    for u, v in globals.G1.edges():
        # If nodes u and v belong to different communities, mark the edge for removal
        if globals.G1.nodes[u]["community"] != globals.G1.nodes[v]["community"]:
            edges_to_remove.append((u, v))

    # Remove the marked edges from the graph
    globals.G1.remove_edges_from(edges_to_remove)

    nx.write_graphml(globals.G1, "G1_graph_output3.graphml")
    breakpoint()
    # set communities to a dictionary
    grouped_addresses = await group_addresses_by_community()
    print(grouped_addresses)

    communities_to_remove = await analyze_communities(grouped_addresses)
    await remove_communities_and_nodes(communities_to_remove)
    remove_inter_community_edges()

    nx.write_graphml(globals.G1, "FINAL_GRAPH_graph3_output.graphml")
    breakpoint()

    print("running heuristics")
    refinedGraph = await sybil_heuristics(globals.G1)
    print("analyzing suspicious clusters")
    print(refinedGraph)
    findings = analyze_suspicious_clusters(refinedGraph) or []

    async with get_async_session() as session:
        await store_graph_clusters(globals.G1, session)

    print("COMPLETE")
    return findings


# TODO: implement active monitoring of identified sybil clusters aside from sliding window
# TODO: sliding window is designed to detect brand new sybils
# TODO: separate analysis structure that takes new transactions and analyzes them in terms of whether or not they are part of previously identified sybils
# TODO: each time transactions are analyzed, check to see if they are either part of an existing community in the global, in memory graph, or part of a new community
# TODO: status for active and inactive communities, alerts for new communities detected
# TODO: make final graph a global variable, window graph should merge into final graph
# TODO: if new activity comes in on accounts already identified as sybils, flag it. monitor sybils specifically as new transactions come in
# TODO: methodology is a progressive narrowing of the aperture
