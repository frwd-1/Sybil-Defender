import networkx as nx

transaction_counter = 0
database_initialized = False
# TODO: consider implementing a directed or multigraph instead of undirected to enhance louvain. look into louvain directed version
G1 = nx.Graph()
