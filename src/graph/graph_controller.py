from src.utils import globals
from collections import defaultdict
import decimal


def add_transactions_to_graph(transfers):
    for transfer in transfers:
        if transfer.sender is not None and transfer.receiver is not None:
            globals.G1.add_edge(
                transfer.sender,
                transfer.receiver,
                timestamp=transfer.timestamp,
                gas_price=transfer.gas_price,
                amount=transfer.amount,
            )
        else:
            print(
                f"Skipping edge addition for transfer with sender={transfer.sender} and receiver={transfer.receiver}"
            )


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
            globals.G1.add_edge(node, target, weight=adjusted_weight)
            processed_edges.add((node, target))

    print("edges added to graph")


def convert_decimal_to_float():
    for _, data in globals.G1.nodes(data=True):
        for key, value in data.items():
            if isinstance(value, decimal.Decimal):
                data[key] = float(value)

    for _, _, data in globals.G1.edges(data=True):
        for key, value in data.items():
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
