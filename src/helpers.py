from src.constants import AMOUNT_TOLERANCE

# from sklearn.cluster import DBSCAN
# import numpy as np


# async def average_jaccard_similarity(transactions_dict):
#     addresses = list(transactions_dict.keys())
#     total_similarity = 0
#     total_pairs = 0

#     for i in range(len(addresses)):
#         for j in range(i + 1, len(addresses)):
#             similarity = await sequence_similarity(
#                 transactions_dict[addresses[i]], transactions_dict[addresses[j]]
#             )
#             total_similarity += similarity
#             total_pairs += 1

#     return total_similarity / total_pairs if total_pairs > 0 else 0


# Helper Functions
async def extract_activity_pairs(activities):
    print(f"Extracting activity pairs from activities: {activities}")
    pairs = set()
    n = len(activities)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.add((activities[i], activities[j]))
    print(f"Extracted pairs: {pairs}")
    return pairs


async def jaccard_similarity(pairs1, pairs2):
    print(f"Calculating Jaccard similarity between {pairs1} and {pairs2}")

    # Helper function to check if two activities are similar
    def activities_similar(act1, act2):
        # Check method ID and contract address
        if act1[0] != act2[0] or act1[2] != act2[2]:
            return False
        # Check transaction amount with tolerance
        return abs(act1[1] - act2[1]) <= AMOUNT_TOLERANCE * act1[1]

    intersection = sum(
        1
        for pair in pairs1
        if any(activities_similar(pair, other_pair) for other_pair in pairs2)
    )
    union = len(pairs1) + len(pairs2) - intersection

    similarity = intersection / union if union != 0 else 0
    print(f"Jaccard similarity: {similarity}")
    return similarity


# async def sequence_similarity(seq1, seq2):
#     print(f"Calculating sequence similarity between {seq1} and {seq2}")
#     pairs1 = await extract_activity_pairs(seq1)
#     pairs2 = await extract_activity_pairs(seq2)
#     return await jaccard_similarity(pairs1, pairs2)
