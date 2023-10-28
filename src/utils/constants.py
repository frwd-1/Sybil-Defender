# transaction counter threshold. ie, every N transactions process_clusters is run
# TODO: may need to adjust for L2 chains
N = 1000

WINDOW_SIZE = 50000
COMMUNITY_SIZE = 5
# similarity threshold checks the similarity of account activities
SIMILARITY_THRESHOLD = 0.5
# interaction ratio is the percentage of addresses in a community that need to have interacted with a smart contract in order to proceed with similarity analysis
INTERACTION_RATIO = 0.5
# threshold to run louvain analysis
LOUVAIN_THRESHOLD = 100
# number of neighboring nodes required for inclusion in graph
NEIGHBOR_THRESHOLD = 3
