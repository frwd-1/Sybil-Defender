from analysis.community_analysis.similarity_analysis import (
    similarity_analysis,
)
from src.utils import globals


async def analyze_suspicious_clusters():
    await similarity_analysis()

    final_communities = {
        node: data["community"] for node, data in globals.G1.nodes(data=True)
    }

    for cluster_id in set(final_communities.values()):
        print(f"Analyzing cluster {cluster_id}")
        cluster_nodes = [
            node for node, id in final_communities.items() if id == cluster_id
        ]

        cluster_transactions = [
            globals.G1.nodes[node]["transaction"]
            for node in cluster_nodes
            if "transaction" in globals.G1.nodes[node]
        ]
