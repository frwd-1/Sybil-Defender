from networkx import Graph
from sklearn.cluster import DBSCAN  # For DBSCAN
from datetime import datetime, timedelta
from database.controller import engine, EOA, Transaction
from community import best_partition  # For the Louvain method
from heuristics.advanced_heuristics import (
    sybil_heuristics,
)
from analysis.cluster_analysis import analyze_suspicious_clusters


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


# TODO: call this process transactions
def process_clusters():
    G = Graph()

    with engine.connect() as conn:
        transactions = conn.query(Transaction).all()
        for transaction in transactions:
            G.add_edge(
                transaction.sender, transaction.receiver, weight=transaction.amount
            )

    partitions_louvain = best_partition(G)

    # Apply DBSCAN
    edge_list = [(sender, receiver) for sender, receiver in G.edges()]
    db = DBSCAN(eps=0.5, min_samples=5).fit(edge_list)
    labels = db.labels_
    partitions_dbscan = {
        edge: cluster_id for edge, cluster_id in zip(edge_list, labels)
    }

    final_partitions = partitions_louvain or partitions_dbscan

    # Apply Sybil Heuristics
    suspicious_clusters = sybil_heuristics(G, final_partitions)

    # Apply Typology Analysis
    findings = analyze_suspicious_clusters(suspicious_clusters)

    prune_unrelated_transactions(final_partitions)

    return findings


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
