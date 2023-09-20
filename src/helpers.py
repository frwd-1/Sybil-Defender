from sklearn.cluster import DBSCAN
import numpy as np


# Helper Functions
async def extract_activity_pairs(sequence):
    print(f"Extracting activity pairs from sequence: {sequence}")
    pairs = set()
    n = len(sequence)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.add((sequence[i], sequence[j]))
    print(f"Extracted pairs: {pairs}")
    return pairs


async def jaccard_similarity(set1, set2):
    print(f"Calculating Jaccard similarity between {set1} and {set2}")
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    similarity = intersection / union if union != 0 else 0
    print(f"Jaccard similarity: {similarity}")
    return similarity


async def sequence_similarity(seq1, seq2):
    print(f"Calculating sequence similarity between {seq1} and {seq2}")
    pairs1 = await extract_activity_pairs(seq1)
    pairs2 = await extract_activity_pairs(seq2)
    return await jaccard_similarity(pairs1, pairs2)


# New Function
async def process_community_using_jaccard_dbscan(interactions_dict):
    print("Starting processing using Jaccard and DBSCAN")
    addresses = list(interactions_dict.keys())
    n = len(addresses)
    print(f"Number of addresses: {n}")

    similarity_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(i + 1, n):  # Avoiding redundant calculations
            similarity = await sequence_similarity(
                interactions_dict[addresses[i]], interactions_dict[addresses[j]]
            )
            similarity_matrix[i][j] = similarity_matrix[j][i] = similarity

    print("Finished calculating similarity matrix")

    db = DBSCAN(metric="precomputed", eps=0.5, min_samples=2)
    labels = db.fit_predict(1 - similarity_matrix)
    print(f"DBSCAN labels: {labels}")

    refined_clusters = {addresses[i]: cluster_id for i, cluster_id in enumerate(labels)}
    print(f"Refined clusters: {refined_clusters}")

    return refined_clusters
