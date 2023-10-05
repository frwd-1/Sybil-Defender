from collections import defaultdict
from src.database.db_utils import extract_method_id
from src.utils import globals


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


async def get_unique_senders(contract_transactions):
    return set(transaction.sender for transaction in contract_transactions)


async def build_contract_activity_dict(contract_transactions):
    contract_activity_dict = defaultdict(set)
    for transaction in contract_transactions:
        methodId = extract_method_id(transaction.data)
        activity = (methodId, transaction.contract_address)
        contract_activity_dict[transaction.sender].add(activity)
    return contract_activity_dict


async def compute_similarity(addresses, contract_activity_dict):
    total_similarity = 0
    total_weights = 0
    for addr1 in addresses:
        for addr2 in addresses:
            if addr1 != addr2:
                activities1 = contract_activity_dict[addr1]
                activities2 = contract_activity_dict[addr2]
                similarity = await jaccard_similarity(activities1, activities2)
                weight = len(activities1) + len(activities2)
                total_similarity += similarity * weight
                total_weights += weight
    return total_similarity / total_weights if total_weights > 0 else 0


async def add_contract_transactions_to_graph(contract_transactions, community_id):
    for transaction in contract_transactions:
        if transaction.sender in globals.G1.nodes:
            globals.G1.nodes[transaction.sender]["community"] = community_id
            if transaction.contract_address not in globals.G1.nodes:
                globals.G1.add_node(
                    transaction.contract_address, community=community_id
                )
            globals.G1.add_edge(
                transaction.sender,
                transaction.contract_address,
                weight=int(transaction.amount),
                community=community_id,
            )
