import community as community_louvain
import networkx as nx
from src.utils.constants import COMMUNITY_SIZE, LOUVAIN_THRESHOLD


def run_louvain_algorithm(G1: nx.DiGraph):
    # Getting strongly and weakly connected components
    sccs = [
        G1.subgraph(c).copy()
        for c in nx.strongly_connected_components(G1)
        if len(c) > COMMUNITY_SIZE
    ]
    wccs = [
        G1.subgraph(c).copy()
        for c in nx.weakly_connected_components(G1)
        if len(c) > COMMUNITY_SIZE
    ]

    print(f"Initial SCCs: {len(sccs)}")
    print(f"Initial WCCs: {len(wccs)}")

    communities = {}
    for idx, component in enumerate(sccs, start=1):
        print(
            f"Processing SCC_{idx} with {len(component)} nodes."
        )  # Logging the current component being processed and its size
        assigned_labels = 0  # Counter for assigned labels in the current component
        for node in component:
            community_label = (
                f"SCC_{idx}" if len(component) <= LOUVAIN_THRESHOLD else None
            )
            communities[node] = community_label

            # Logging assignment details
            if community_label is not None:
                assigned_labels += 1
            print(f"Assigned {community_label} to Node {node}.")

        # Log summary of assignments for the current component
        print(
            f"For SCC_{idx}, assigned labels to {assigned_labels} nodes out of {len(component)} total nodes."
        )
        if assigned_labels < len(component):
            print(
                f"NOTE: {len(component) - assigned_labels} nodes in SCC_{idx} received None as community label due to size threshold."
            )

    # Debugging: Print assigned SCC nodes
    assigned_scc_sub_nodes = [
        node
        for node, community in communities.items()
        if community and "SCC_community" in community
    ]
    print(f"Assigned SCC sub-community nodes: {assigned_scc_sub_nodes}")

    for idx, component in enumerate(wccs, start=1):
        for node in component:
            communities[node] = (
                f"WCC_{idx}" if len(component) <= LOUVAIN_THRESHOLD else None
            )

    community_index = 0

    for component in sccs:
        if len(component) > LOUVAIN_THRESHOLD:
            print(f"Running Louvain on large SCC (size: {len(component)})")

            undirected_component = component.to_undirected()
            print(
                f"Converted component to undirected. Number of nodes: {undirected_component.number_of_nodes()}"
            )

            partition = community_louvain.best_partition(undirected_component)
            print(f"Generated partitions using Louvain on large SCC: {partition}")

            for node, sub_community in partition.items():
                print(
                    f"Assigning {node} to community SCC_community_{community_index}_sub_{sub_community}"
                )
                communities[
                    node
                ] = f"SCC_community_{community_index}_sub_{sub_community}"

            community_index += 1
            print(
                f"Finished processing large SCC (new communities assigned, community_index: {community_index})"
            )

    for component in wccs:
        if len(component) > LOUVAIN_THRESHOLD:
            print(f"Running Louvain on large WCC (size: {len(component)})")
            undirected_component = component.to_undirected()
            partition = community_louvain.best_partition(undirected_component)

            for node, sub_community in partition.items():
                communities[
                    node
                ] = f"WCC_community_{community_index}_sub_{sub_community}"

            community_index += 1
            print(f"Finished processing large WCC (new communities assigned)")

    print(f"Total Communities Assigned: {len(set(communities.values()))}")
    return communities
