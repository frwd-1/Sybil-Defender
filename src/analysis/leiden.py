import igraph as ig
import leidenalg
import networkx as nx
from src.utils.constants import COMMUNITY_SIZE


def run_leiden_algorithm(G1: nx.DiGraph, component_types=["SCC", "WCC"]):
    sccs = [G1.subgraph(c).copy() for c in nx.strongly_connected_components(G1)]
    wccs = [G1.subgraph(c).copy() for c in nx.weakly_connected_components(G1)]

    partitions = {}  # Dictionary to store nodes with their associated community IDs
    component_types = ["SCC", "WCC"]

    for component_type, component_list in zip(component_types, [sccs, wccs]):
        for i, component in enumerate(component_list):
            # Create a mapping from NetworkX nodes to integer indices
            mapping = {node: idx for idx, node in enumerate(component.nodes())}
            print(f"Mapping for {component_type}-{i}: {mapping}")

            # Construct the igraph graph using the indices as nodes
            G_igraph = ig.Graph(len(mapping), directed=True)
            for edge in component.edges():
                G_igraph.add_edge(mapping[edge[0]], mapping[edge[1]])

            # Run the Leiden algorithm
            partition = leidenalg.find_partition(
                G_igraph, leidenalg.ModularityVertexPartition
            )

            # Map the igraph indices back to the original node labels
            reverse_mapping = {idx: node for node, idx in mapping.items()}
            print(f"Reverse Mapping for {component_type}-{i}: {reverse_mapping}")

            # iterate over the partition and associate original node labels with communities
            for community_id, community_nodes in enumerate(partition):
                for node in community_nodes:
                    try:
                        original_node_label = reverse_mapping[node]
                        partitions[
                            original_node_label
                        ] = f"{component_type}_{i}_{community_id}"
                    except KeyError:
                        print(
                            f"Warning: Node {node} not found in reverse mapping for {component_type}-{i}. Skipping."
                        )
                        continue

    # Remove communities smaller than the specified size
    to_remove = [
        node
        for node, community in partitions.items()
        if list(partitions.values()).count(community) < COMMUNITY_SIZE
    ]
    for node in to_remove:
        del partitions[node]

    return partitions
