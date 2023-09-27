async def extract_activity_pairs(activities):
    print(f"Extracting activity pairs from activities: {activities}")
    pairs = set()
    n = len(activities)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.add((activities[i], activities[j]))
    print(f"Extracted pairs: {pairs}")
    return pairs


async def jaccard_similarity(set1, set2):
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    similarity = intersection / union if union != 0 else 0
    return similarity
