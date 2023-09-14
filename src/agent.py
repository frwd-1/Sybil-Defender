import logging
from networkx import Graph
from sklearn.cluster import DBSCAN  # For DBSCAN
from datetime import datetime, timedelta
from database.controller import engine, EOA, Transaction
from community import best_partition  # For the Louvain method
from heuristics.advanced_heuristics import sybil_heuristics
from analysis.cluster_analysis import analyze_suspicious_clusters

# Logger setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
LOG_ENABLED = True  # Global switch to enable or disable logging

# TODO: create a constants file
N = 100


def analyze_transaction(transaction_event):
    global transaction_counter

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

    if LOG_ENABLED:
        logger.info(f"Processed transaction: {tx_hash}")

    transaction_counter += 1
    if transaction_counter >= N:
        if LOG_ENABLED:
            logger.info("Reached threshold, processing clusters...")
        process_clusters()
        transaction_counter = 0


def process_clusters():
    G = Graph()

    with engine.connect() as conn:
        transactions = conn.query(Transaction).all()
        for transaction in transactions:
            G.add_edge(
                transaction.sender, transaction.receiver, weight=transaction.amount
            )

    partitions_louvain = best_partition(G)
    edge_list = [(sender, receiver) for sender, receiver in G.edges()]
    db = DBSCAN(eps=0.5, min_samples=5).fit(edge_list)
    labels = db.labels_
    partitions_dbscan = {
        edge: cluster_id for edge, cluster_id in zip(edge_list, labels)
    }

    final_partitions = partitions_louvain or partitions_dbscan
    suspicious_clusters = sybil_heuristics(G, final_partitions)
    findings = analyze_suspicious_clusters(suspicious_clusters)

    if LOG_ENABLED:
        logger.info(f"Found {len(findings)} suspicious clusters")

    prune_unrelated_transactions(final_partitions)
    return findings


def prune_unrelated_transactions(partitions):
    cluster_transactions = set()
    for (sender, receiver), cluster_id in partitions.items():
        if cluster_id != -1:
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

    if LOG_ENABLED:
        logger.info("Pruned unrelated transactions")
