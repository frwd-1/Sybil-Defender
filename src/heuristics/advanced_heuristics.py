from datetime import timedelta


def sybil_heuristics(G, partitions):
    suspicious_clusters = []

    for cluster, nodes in partitions.items():
        intra_transactions = sum(
            [G[u][v]["weight"] for u in nodes for v in nodes if v in G[u]]
        )
        inter_transactions = sum(
            [
                G[u][v]["weight"]
                for u in nodes
                for v in G
                if v not in nodes and v in G[u]
            ]
        )

        # Check intra/inter transaction ratio
        if intra_transactions > (
            inter_transactions * 2
        ):  # Adjust the ratio based on your needs
            suspicious_clusters.append(cluster)
            continue  # No need to check other heuristics for this cluster, move to the next

        # TODO: set thresholds as environment variables
        for node in nodes:
            # Check transaction diversity
            diversity = transaction_diversity_heuristic(node, G)
            if diversity < 0.5:  # Define SOME_DIVERSITY_THRESHOLD
                suspicious_clusters.append(cluster)
                break  # One suspicious node is enough to flag the cluster, move to the next cluster

            # Check account age
            if account_age_heuristic(
                node, G
            ):  # Assume you have G available here too, or pass another necessary parameter
                suspicious_clusters.append(cluster)
                break  # One suspicious node is enough to flag the cluster, move to the next cluster

    return suspicious_clusters


def transaction_diversity_heuristic(node, G):
    neighbors = list(G.neighbors(node))
    return len(neighbors) / sum([G[node][neighbor]["weight"] for neighbor in neighbors])


def account_age_heuristic(node, G):  # Adjust parameters as needed
    # TODO: Fetch the account age
    age = None  # this needs to be defined

    transactions_count = len(list(G.neighbors(node)))
    if (
        age < timedelta(days=30) and transactions_count > 100
    ):  # Define SOME_THRESHOLD and ANOTHER_THRESHOLD
        return True
    return False
