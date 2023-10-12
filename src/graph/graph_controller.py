from src.utils import globals
from src.utils.constants import COMMUNITY_SIZE
from collections import defaultdict
import decimal


# TODO: refactor module for clarity
# community_merger.py


def merge_new_communities(partitions, previous_communities, added_edges, G1):
    connected_new_communities = set()
    for edge in added_edges:
        src_node, dest_node = edge
        if src_node in previous_communities:
            connected_new_communities.add(partitions[dest_node])
        if dest_node in previous_communities:
            connected_new_communities.add(partitions[src_node])

    for node, community in partitions.items():
        if community in connected_new_communities:
            for edge in G1.edges(node):
                if edge[0] in previous_communities:
                    partitions[node] = previous_communities[edge[0]]
                    break
                elif edge[1] in previous_communities:
                    partitions[node] = previous_communities[edge[1]]
                    break

    max_existing_community_id = max(previous_communities.values())
    new_community_id = max_existing_community_id + 1
    for node, community in partitions.items():
        if (
            node not in previous_communities
            and community not in connected_new_communities
        ):
            partitions[node] = new_community_id
            new_community_id += 1

    return partitions


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
                amount_var = abs(primary_edge[2]["amount"] - adj_edge[2]["amount"])
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


def process_partitions(partitions):
    for node, community in partitions.items():
        globals.G1.nodes[node]["community"] = community

    # Calculate the size of each community
    community_sizes = {}
    for node, data in globals.G1.nodes(data=True):
        community = data.get("community")
        if community is not None:
            community_sizes[community] = community_sizes.get(community, 0) + 1

    # Identify and remove nodes that belong to small communities or have no community
    nodes_to_remove = [
        node
        for node, data in globals.G1.nodes(data=True)
        if data.get("community") is None
        or community_sizes.get(data.get("community"), 0) < COMMUNITY_SIZE
    ]
    globals.G1.remove_nodes_from(nodes_to_remove)

    # This will store edges that need to be removed
    edges_to_remove = []

    # Iterate over all edges of the graph
    for u, v in globals.G1.edges():
        # If nodes u and v belong to different communities or one of them doesn't have a community, mark the edge for removal
        u_community = globals.G1.nodes[u].get("community")
        v_community = globals.G1.nodes[v].get("community")
        if u_community is None or v_community is None or u_community != v_community:
            edges_to_remove.append((u, v))

    # Remove the marked edges from the graph
    globals.G1.remove_edges_from(edges_to_remove)

    # Additional step to remove isolated nodes
    isolated_nodes = [
        node for node in globals.G1.nodes() if globals.G1.degree(node) == 0
    ]
    globals.G1.remove_nodes_from(isolated_nodes)
