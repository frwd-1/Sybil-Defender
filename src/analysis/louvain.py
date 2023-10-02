import community as community_louvain
import networkx as nx
from src.utils.constants import COMMUNITY_SIZE, LOUVAIN_THRESHOLD


def run_louvain_algorithm(G1: nx.DiGraph):
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
    community_index = 1  # Start community_index at 1

    for idx, component in enumerate(sccs, start=1):
        print(f"Processing SCC_{idx} with {len(component)} nodes.")
        if len(component) <= LOUVAIN_THRESHOLD:
            for node in component:
                communities[node] = community_index
                print(f"Assigned community {community_index} to Node {node}.")
            community_index += 1  # Increment community_index after assigning it to all nodes in the component
        else:
            print(f"Running Louvain on large SCC (size: {len(component)})")
            undirected_component = component.to_undirected()
            partition = community_louvain.best_partition(undirected_component)
            print(f"Generated partitions using Louvain on large SCC: {partition}")

            unique_sub_communities = set(partition.values())
            for sub_community in unique_sub_communities:
                for node, community in partition.items():
                    if community == sub_community:
                        communities[node] = community_index
                        print(f"Assigning {node} to community {community_index}")
                community_index += 1

    for idx, component in enumerate(wccs, start=1):
        print(f"Processing WCC_{idx} with {len(component)} nodes.")
        if len(component) <= LOUVAIN_THRESHOLD:
            for node in component:
                if node not in communities:  # Prevent overwriting SCC communities
                    communities[node] = community_index
                    print(f"Assigned community {community_index} to Node {node}.")
            community_index += 1  # Increment community_index after assigning it to all nodes in the component
        else:
            print(f"Running Louvain on large WCC (size: {len(component)})")
            undirected_component = component.to_undirected()
            partition = community_louvain.best_partition(undirected_component)
            print(f"Generated partitions using Louvain on large WCC: {partition}")

            unique_sub_communities = set(partition.values())
            for sub_community in unique_sub_communities:
                for node, community in partition.items():
                    if community == sub_community and node not in communities:
                        communities[node] = community_index
                        print(f"Assigning {node} to community {community_index}")
                community_index += 1

    print(f"Total Communities Assigned: {len(set(communities.values()))}")
    return communities
