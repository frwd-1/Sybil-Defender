from sklearn.cluster import DBSCAN
import numpy as np


async def average_jaccard_similarity(transactions_dict):
    addresses = list(transactions_dict.keys())
    total_similarity = 0
    total_pairs = 0

    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            similarity = await sequence_similarity(
                transactions_dict[addresses[i]], transactions_dict[addresses[j]]
            )
            total_similarity += similarity
            total_pairs += 1

    return total_similarity / total_pairs if total_pairs > 0 else 0


# Helper Functions
async def extract_activity_pairs(sequence):
    print(f"Extracting activity pairs from sequence: {sequence}")
    pairs = set()
    n = len(sequence)
    for i in range(n):
        for j in range(i + 1, n):
            activity_i = (sequence[i]["function_name"], sequence[i]["params"])
            activity_j = (sequence[j]["function_name"], sequence[j]["params"])
            pairs.add((activity_i, activity_j))
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
