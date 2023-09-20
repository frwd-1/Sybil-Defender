from sklearn.cluster import DBSCAN
import numpy as np


# Helper Functions
async def extract_activity_pairs(sequence):
    pairs = set()
    n = len(sequence)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.add((sequence[i], sequence[j]))
    return pairs


async def jaccard_similarity(set1, set2):
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union != 0 else 0


async def sequence_similarity(seq1, seq2):
    pairs1 = await extract_activity_pairs(seq1)
    pairs2 = await extract_activity_pairs(seq2)
    return await jaccard_similarity(pairs1, pairs2)


# New Function
async def process_community_using_jaccard_dbscan(interactions_dict):
    addresses = list(interactions_dict.keys())
    n = len(addresses)
    similarity_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            similarity_matrix[i][j] = sequence_similarity(
                interactions_dict[addresses[i]], interactions_dict[addresses[j]]
            )

    db = DBSCAN(metric="precomputed", eps=0.5, min_samples=2)
    labels = db.fit_predict(1 - similarity_matrix)

    refined_clusters = {addresses[i]: cluster_id for i, cluster_id in enumerate(labels)}
    return refined_clusters
