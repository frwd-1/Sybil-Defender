from networkx import Graph
from community import best_partition  # For the Louvain method
from sklearn.cluster import DBSCAN  # For DBSCAN
from datetime import datetime, timedelta

from controller import engine, EOA, Transaction


def analyze_transaction(transaction_event):
    tx_hash = transaction_event.hash
    sender = transaction_event.from_
    receiver = transaction_event.to
    amount = transaction_event.transaction.value

    with engine.connect() as conn:
        conn.add(EOA(address=sender))
        conn.add(EOA(address=receiver))
        conn.add(
            Transaction(
                tx_hash=tx_hash, sender=sender, receiver=receiver, amount=amount
            )
        )
        conn.commit()


def process_clusters():
    G = Graph()

    with engine.connect() as conn:
        transactions = conn.query(Transaction).all()
        for transaction in transactions:
            G.add_edge(
                transaction.sender, transaction.receiver, weight=transaction.amount
            )

    # Apply Louvain
    partitions_louvain = best_partition(G)

    # Apply DBSCAN
    edge_list = [
        (transaction.sender, transaction.receiver) for transaction in transactions
    ]
    db = DBSCAN(eps=0.5, min_samples=5).fit(edge_list)
    labels = db.labels_
    partitions_dbscan = {
        edge: cluster_id for edge, cluster_id in zip(edge_list, labels)
    }

    final_partitions = partitions_louvain or partitions_dbscan

    # Print clusters
    for node, cluster_id in final_partitions.items():
        print(f"Node {node} belongs to cluster {cluster_id}")

    prune_unrelated_transactions(final_partitions)


def prune_unrelated_transactions(partitions):
    cluster_transactions = set()
    for (sender, receiver), cluster_id in partitions.items():
        if cluster_id != -1:  # For DBSCAN, -1 indicates noise, not part of any cluster
            with engine.connect() as conn:
                txs = (
                    conn.query(Transaction)
                    .filter(
                        Transaction.sender == sender, Transaction.receiver == receiver
                    )
                    .all()
                )
                for tx in txs:
                    cluster_transactions.add(tx.tx_hash)

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    with engine.connect() as conn:
        old_txs = (
            conn.query(Transaction)
            .filter(Transaction.timestamp < thirty_days_ago)
            .all()
        )
        for tx in old_txs:
            if tx.tx_hash not in cluster_transactions:
                conn.delete(tx)
        conn.commit()
