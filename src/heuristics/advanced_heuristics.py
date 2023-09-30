from datetime import timedelta
from src.database.models import SybilClusters
from collections import defaultdict
from src.database.db_controller import get_async_session


async def sybil_heuristics(G):
    suspicious_clusters = []

    # Construct partitions from the community attribute of nodes in the graph
    new_partitions = defaultdict(list)
    for node, data in G.nodes(data=True):
        print(data)
        if "community" in data:
            community_id = data["community"]
        else:
            continue

        new_partitions[community_id].append(node)

    print("checking nodes in partitions")

    for cluster_id, nodes in new_partitions.items():
        print("checking intra transactions")
        intra_transactions = sum(
            [G[u][v].get("weight", 0) for u in nodes for v in nodes if v in G[u]]
        )
        print("checking inter transactions")
        inter_transactions = sum(
            [
                G[u][v].get("weight", 0)
                for u in nodes
                for v in G
                if v not in nodes and v in G[u]
            ]
        )

        # Check intra/inter transaction ratio
        print("inter / intra transaction ratio check")
        if intra_transactions > (inter_transactions * 2):
            suspicious_clusters.append(cluster_id)
            continue

        # TODO: set thresholds as environment variables
        for node in nodes:
            # Check transaction diversity
            print("running transaction diversity heuristic")
            diversity = transaction_diversity_heuristic(node, G)
            if diversity < 0.5:
                print("diversity threshold met, adding to cluster")
                suspicious_clusters.append(cluster_id)
                break

            # Check account age
            print("checking account age heuristic")
            if account_age_heuristic(node, G):
                print("account age threshold met, adding to cluster")
                suspicious_clusters.append(cluster_id)
                break

    print("heuristic checks finished")

    # Once suspicious clusters are identified, we prune G and partitions
    nodes_to_retain = set()

    # Collect nodes associated with suspicious clusters
    for cluster_id in suspicious_clusters:
        nodes_to_retain.update(new_partitions[cluster_id])

    # Remove nodes from G that are not part of suspicious clusters
    for node in list(G.nodes()):
        if node not in nodes_to_retain:
            G.remove_node(node)

    await store_suspicious_clusters(suspicious_clusters, new_partitions)

    return G


async def store_suspicious_clusters(suspicious_clusters, new_partitions):
    async with get_async_session() as session:
        for cluster_id in suspicious_clusters:
            for node in new_partitions[cluster_id]:
                new_entry = SybilClusters(cluster_id, node)
                session.add(new_entry)

        await session.commit()


def transaction_diversity_heuristic(node, G):
    neighbors = list(G.neighbors(node))
    total_weight = sum([G[node][neighbor].get("weight", 0) for neighbor in neighbors])

    if total_weight == 0:
        return 0

    return len(neighbors) / total_weight


def account_age_heuristic(node, G):
    age = None  # you need to define how you get the age

    transactions_count = len(list(G.neighbors(node)))
    if age and age < timedelta(days=30) and transactions_count > 100:
        return True
    return False
