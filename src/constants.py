# transaction counter threshold. ie, every N transactions process_clusters is run
N = 50000
WINDOW_SIZE = 50000000
COMMUNITY_SIZE = 15
SIMILARITY_THRESHOLD = 0.1
# interaction ratio is the percentage of addresses in a community that need to have interacted with a smart contract in order to proceed with similarity analysis
INTERACTION_RATIO = 0.3
# tolerance for the difference in transaction amount for jaccard similarity
AMOUNT_TOLERANCE = 1, 000, 000, 000, 000, 000, 000
