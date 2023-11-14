import networkx as nx

transaction_counter = 0
database_initialized = False
# TODO: consider implementing a directed or multigraph instead of undirected to enhance louvain. look into louvain directed version
G1 = nx.DiGraph()
G2 = nx.DiGraph()
is_initial_batch = True
# global_added_edges = []
previous_communities = {}
is_graph_initialized = False

all_transfers = 0
all_contract_transactions = 0
sybil_transfers = 0
sybil_contract_transactions = 0
