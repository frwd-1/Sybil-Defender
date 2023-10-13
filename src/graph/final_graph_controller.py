import networkx as nx


def save_graph(graph, filename):
    nx.write_graphml(graph, filename)


def load_graph(filename):
    return nx.read_graphml(filename)


def merge_graphs(G1, final_graph):
    for node, attr in G1.nodes(data=True):
        if attr.get("status") == "suspicious":
            if node not in final_graph:
                final_graph.add_node(node, **attr)
                for neighbor in G1.neighbors(node):
                    if G1.nodes[neighbor].get("status") == "suspicious":
                        final_graph.add_edge(node, neighbor, **G1[node][neighbor])
            else:
                # If node is already in the final graph, merge the communities
                final_community_id = final_graph.nodes[node]["community"]
                G1_community_id = G1.nodes[node]["community"]

                # Update nodes in G1 with the community ID from the final graph
                for n, a in G1.nodes(data=True):
                    if a.get("community") == G1_community_id:
                        a["community"] = final_community_id

                # Add nodes and edges from G1's community to final graph
                nodes_in_G1_community = [
                    n
                    for n, a in G1.nodes(data=True)
                    if a.get("community") == final_community_id
                ]
                final_graph = nx.compose(
                    final_graph, G1.subgraph(nodes_in_G1_community)
                )

    return final_graph
