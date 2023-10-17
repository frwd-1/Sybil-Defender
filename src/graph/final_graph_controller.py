import networkx as nx


def save_graph(graph, filename):
    nx.write_graphml(graph, filename)


def load_graph(filename):
    return nx.read_graphml(filename)
