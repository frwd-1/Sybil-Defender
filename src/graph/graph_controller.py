from src.utils import globals
from src.utils.constants import COMMUNITY_SIZE
from collections import defaultdict
import decimal
from src.database.db_controller import get_async_session
from sqlalchemy.future import select
from src.database.models import Transfer
from src.utils import globals
import networkx as nx


# TODO: refactor module for clarity


async def initialize_global_graph():
    async with get_async_session() as session:
        result = await session.execute(select(Transfer))
        all_transfers = result.scalars().all()
        added_edges = add_transactions_to_graph(all_transfers)
        globals.global_added_edges.extend(added_edges)
        adjust_edge_weights_and_variances(all_transfers)
        convert_decimal_to_float()


def merge_new_communities(updated_subgraph):
    print("Starting merge of new communities...")

    G2 = globals.G2
    previous_communities = nx.get_node_attributes(G2, "community")
    print(f"Number of communities in G2: {len(set(previous_communities.values()))}")

    overlapping_nodes = set(G2.nodes()).intersection(updated_subgraph.nodes())
    print(f"Overlapping nodes: {overlapping_nodes}")

    # Step 1: Merge overlapping communities
    merged_communities = (
        set()
    )  # To keep track of communities in the subgraph that get merged
    for node in overlapping_nodes:
        target_community = previous_communities[node]
        subgraph_community = updated_subgraph.nodes[node]["community"]

        # If the community has not been merged yet
        if subgraph_community not in merged_communities:
            merged_communities.add(subgraph_community)

            # Update community of nodes in updated_subgraph
            for n, d in updated_subgraph.nodes(data=True):
                if d["community"] == subgraph_community:
                    d["community"] = target_community
                    print(
                        f"Updating node {n} from community {subgraph_community} to {target_community}."
                    )

    # Step 2: Identify and assign new IDs to non-overlapping communities
    max_existing_community_id = max(previous_communities.values(), default=0)
    new_community_id = max_existing_community_id + 1
    print(f"Starting new community IDs from: {new_community_id}")

    subgraph_communities = set(
        data["community"] for _, data in updated_subgraph.nodes(data=True)
    )
    for community in subgraph_communities:
        if (
            community not in previous_communities.values()
            and community not in merged_communities
        ):
            for n, d in updated_subgraph.nodes(data=True):
                if d["community"] == community:
                    d["community"] = new_community_id
                    print(f"Assigning new community ID {new_community_id} to node {n}.")
            new_community_id += 1

    # Step 3: Add updated nodes and edges to G2
    G2.add_nodes_from(updated_subgraph.nodes(data=True))
    G2.add_edges_from(updated_subgraph.edges(data=True))

    print("Completed merge of new communities.")


def add_transactions_to_graph(transfers):
    added_edges = []
    for transfer in transfers:
        if transfer.sender is not None and transfer.receiver is not None:
            globals.G1.add_edge(
                transfer.sender,
                transfer.receiver,
                timestamp=transfer.timestamp,
                gas_price=transfer.gas_price,
                amount=transfer.amount,
            )
            added_edges.append((transfer.sender, transfer.receiver))
        else:
            print(
                f"Skipping edge addition for transfer with sender={transfer.sender} and receiver={transfer.receiver}"
            )
    return added_edges


def adjust_edge_weights_and_variances(transfers):
    # TODO: CHeck loGIC??
    # TODO: Update edge weights based on variance
    # TODO: place edge weight logic in heuristic module
    edge_weights = defaultdict(int)
    for transfer in transfers:
        edge = (transfer.sender, transfer.receiver)
        edge_weights[edge] += 1

    processed_edges = set()
    for node in globals.G1.nodes():
        for primary_edge in globals.G1.edges(node, data=True):
            if (node, primary_edge[1]) in processed_edges or (
                primary_edge[1],
                node,
            ) in processed_edges:
                continue

            target = primary_edge[1]
            variances = []

            for adj_edge in globals.G1.edges(target, data=True):
                # TODO: is float ok here?
                gas_price_var = abs(
                    float(primary_edge[2]["gas_price"])
                    - float(adj_edge[2]["gas_price"])
                )
                amount_var = abs(
                    float(primary_edge[2]["amount"]) - float(adj_edge[2]["amount"])
                )

                timestamp_var = abs(
                    primary_edge[2]["timestamp"] - adj_edge[2]["timestamp"]
                )

                variances.append(
                    gas_price_var + float(amount_var) + float(timestamp_var)
                )

            # Take mean variance for primary edge
            mean_variance = sum(variances) / len(variances) if variances else 0

            # Adjust the weight
            initial_weight = edge_weights[(node, target)]

            adjusted_weight = (1 / (mean_variance + 1)) * initial_weight

            # Update the edge in the graph
            globals.G1.add_edge(node, target, weight=adjusted_weight)
            processed_edges.add((node, target))

    print("edges added to graph")


def convert_decimal_to_float():
    for node, data in globals.G1.nodes(data=True):
        for key, value in data.items():
            if isinstance(value, list):
                print(f"Node {node} has list data: {key} = {value}")
            if isinstance(value, decimal.Decimal):
                data[key] = float(value)

    for u, v, data in globals.G1.edges(data=True):
        for key, value in data.items():
            if isinstance(value, list):
                print(f"Edge ({u}, {v}) has list data: {key} = {value}")
            if isinstance(value, decimal.Decimal):
                data[key] = float(value)


async def remove_communities_and_nodes(communities_to_remove):
    nodes_to_remove = [
        node
        for node, data in globals.G1.nodes(data=True)
        if data.get("community") in communities_to_remove
    ]
    globals.G1.remove_nodes_from(nodes_to_remove)


def remove_inter_community_edges():
    inter_community_edges = [
        (u, v)
        for u, v in globals.G1.edges()
        if globals.G1.nodes[u]["community"] != globals.G1.nodes[v]["community"]
    ]
    globals.G1.remove_edges_from(inter_community_edges)
    print(f"Removed {len(inter_community_edges)} inter-community edges from G1.")


def process_partitions(partitions, subgraph):
    print("Processing partitions...")

    for node, community in partitions.items():
        subgraph.nodes[node]["community"] = community

    print("Partitions processed.")

    # Calculate the size of each community
    community_sizes = {}
    for node, data in subgraph.nodes(data=True):
        community = data.get("community")
        if community is not None:
            community_sizes[community] = community_sizes.get(community, 0) + 1

    print(f"Community sizes calculated: {community_sizes}")

    # Identify and remove nodes that belong to small communities or have no community
    nodes_to_remove = [
        node
        for node, data in subgraph.nodes(data=True)
        if data.get("community") is None
        or community_sizes.get(data.get("community"), 0) < COMMUNITY_SIZE
    ]

    print(f"Identified nodes to remove: {len(nodes_to_remove)}")
    # TODO: change to subgraph
    subgraph.remove_nodes_from(nodes_to_remove)
    print("Nodes removed.")

    edges_to_remove = []

    # Iterate over all edges of the graph
    for u, v in subgraph.edges():
        # Fetch the community attributes for nodes u and v
        u_community = subgraph.nodes[u].get("community")
        v_community = subgraph.nodes[v].get("community")

        print(
            f"Edge ({u}, {v}): Node {u} has community {u_community}. Node {v} has community {v_community}."
        )

        # If nodes u and v belong to different communities or one of them doesn't have a community, mark the edge for removal
        if u_community is None or v_community is None or u_community != v_community:
            print(
                f"Marking edge ({u}, {v}) for removal due to differing or absent communities."
            )
            edges_to_remove.append((u, v))

    print(f"Identified edges to remove: {len(edges_to_remove)}")
    # Remove the marked edges from the graph
    subgraph.remove_edges_from(edges_to_remove)
    print("Edges removed.")

    # Additional step to remove isolated nodes
    isolated_nodes = [node for node in subgraph.nodes() if subgraph.degree(node) == 0]
    print(f"Identified isolated nodes to remove: {len(isolated_nodes)}")
    subgraph.remove_nodes_from(isolated_nodes)
    print("Isolated nodes removed.")

    print("Processing completed.")

    return subgraph
