from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, and_
from sqlalchemy.pool import QueuePool
from networkx import Graph
from community import best_partition  # Louvain method
from sklearn.cluster import DBSCAN
import numpy as np

DATABASE_URL = "your_db_url_here"  # placeholder

# Connection pooling
engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=10)


async def analyze_transaction(transaction_event: transaction_event):
    tx_hash = transaction_event.hash
    sender = transaction_event.from_
    receiver = transaction_event.to
    amount = transaction_event.transaction.value

    with engine.connect() as conn:
        # Upsert mechanism
        conn.execute(eoas.insert().values(address=sender).on_conflict_do_nothing())
        conn.execute(eoas.insert().values(address=receiver).on_conflict_do_nothing())

        # Insert transaction details with upsert (assuming tx_hash is unique)
        conn.execute(
            transactions.insert()
            .values(tx_hash=tx_hash, sender=sender, receiver=receiver, amount=amount)
            .on_conflict("tx_hash")
            .do_update()
            .values(sender=sender, receiver=receiver, amount=amount)
        )


def louvain_clustering(G):
    return best_partition(G)


def dbscan_clustering(G):
    # Convert your graph into a format suitable for DBSCAN.
    # This might involve creating an adjacency matrix or some similar representation.
    # Assuming `matrix` is your adjacency matrix:
    matrix = np.array(nx.to_numpy_matrix(G))
    clustering = DBSCAN(eps=0.5, min_samples=2).fit(matrix)
    return clustering.labels_


def process_clusters():
    G = Graph()

    # Load data from DB into the graph
    with engine.connect() as conn:
        for row in conn.execute(transactions.select()):
            G.add_edge(row["sender"], row["receiver"], weight=row["amount"])

    # Apply Louvain
    partitions_louvain = louvain_clustering(G)

    # Apply DBSCAN
    partitions_dbscan = dbscan_clustering(G)

    # Decision mechanism (you could intersect, union, or have some other mechanism)
    # This is a simple example where we just print out both results.
    # In a real scenario, you'd want a more sophisticated way to merge or choose between them.
    for node, cluster_id in partitions_louvain.items():
        print(f"[Louvain] Node {node} belongs to cluster {cluster_id}")

    for index, cluster_id in enumerate(partitions_dbscan):
        node = G.nodes()[index]
        print(f"[DBSCAN] Node {node} belongs to cluster {cluster_id}")


# old.....
# Create graph and apply Louvain method
# def process_clusters():
#     G = Graph()

#     # Load data from DB into the graph
#     with engine.connect() as conn:
#         for row in conn.execute(transactions.select()):
#             G.add_edge(row["sender"], row["receiver"], weight=row["amount"])

#     # Apply Louvain
#     partitions = best_partition(G)

#     # For now, just print clusters; can be stored or further processed
#     for node, cluster_id in partitions.items():
#         print(f"Node {node} belongs to cluster {cluster_id}")

#     # Optional: Prune unrelated transactions
#     unrelated_txs = []  # logic to determine these
#     with engine.connect() as conn:
#         for tx in unrelated_txs:
#             conn.execute(transactions.delete().where(transactions.c.tx_hash == tx))
