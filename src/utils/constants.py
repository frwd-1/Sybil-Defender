# transaction counter threshold. ie, every N transactions process_clusters is run
N = 100
WINDOW_SIZE = 500
COMMUNITY_SIZE = 5
# similarity threshold checks the similarity of account activities
SIMILARITY_THRESHOLD = 0.5
# interaction ratio is the percentage of addresses in a community that need to have interacted with a smart contract in order to proceed with similarity analysis
INTERACTION_RATIO = 0.7
# threshold to run louvain analysis
LOUVAIN_THRESHOLD = 100
# number of neighboring nodes required for inclusion in graph
NEIGHBOR_THRESHOLD = 3
