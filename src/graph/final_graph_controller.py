import networkx as nx


def save_graph(graph, filename):
    nx.write_graphml(graph, filename)


def load_graph(filename):
    return nx.read_graphml(filename)


def merge_graphs(G1, persistent_graph):
    for node, attr in G1.nodes(data=True):
        if attr.get("status") == "suspicious":
            # Check if the node has a "community" attribute in G1
            G1_community_id = attr.get("community", None)
            if G1_community_id is None:
                continue  # Skip this node, as it doesn't have a community ID in G1

            # If the node is not in the persistent graph, add it and its associated edges
            if node not in persistent_graph:
                persistent_graph.add_node(node, **attr)
                for neighbor in G1.neighbors(node):
                    if G1.nodes[neighbor].get("status") == "suspicious":
                        persistent_graph.add_edge(node, neighbor, **G1[node][neighbor])

            else:
                # If node is already in the persistent graph, check if it has a "community" attribute
                if "community" in persistent_graph.nodes[node]:
                    persistent_community_id = persistent_graph.nodes[node]["community"]

                    # Update nodes in G1 with the community ID from the persistent graph
                    for n, a in G1.nodes(data=True):
                        if a.get("community") == G1_community_id:
                            a["community"] = persistent_community_id

                    # Add nodes and edges from G1's community to persistent graph
                    nodes_in_G1_community = [
                        n
                        for n, a in G1.nodes(data=True)
                        if a.get("community") == persistent_community_id
                    ]
                    persistent_graph = nx.compose(
                        persistent_graph, G1.subgraph(nodes_in_G1_community)
                    )

    return persistent_graph
