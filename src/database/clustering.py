import datetime
from src.utils import globals

from src.database.models import SybilClusters

from sqlalchemy.future import select
from src.database.db_controller import get_async_session


from Crypto.Hash import keccak
from forta_agent import Finding, FindingSeverity, FindingType, EntityType


async def write_graph_to_database():
    findings = []

    async with get_async_session() as session:
        # Load all existing nodes from the database for comparison
        existing_nodes = await load_all_nodes_from_database(session)

        # Iterate and filter through graph nodes with 'label' attribute
        for node, data in globals.G1.nodes(data=True):
            if "label" in data:
                label = data["label"]
                community_id = data.get("community")

                # Check if node already exists
                existing_node = existing_nodes.get(node)

                # If new labeled node or label has changed, generate a finding
                if not existing_node or existing_node.labels != label:
                    alert_details = generate_alert_details(node, community_id, label)
                    findings.append(Finding(alert_details))

                # If node doesn't exist or label has changed, insert or update in database
                if not existing_node or existing_node.labels != label:
                    new_cluster = SybilClusters(
                        cluster_id=community_id, address=node, labels=label
                    )

                    session.merge(new_cluster)

        await session.commit()

    return findings


def generate_alert_details(node, community_id, label):
    alert_details = {
        "name": "Sybil Airdrop Farmer Detected",
        "description": f"Node {node} in Cluster {community_id} shows signs of {label}",
        "alert_id": keccak.new(
            data=f"{label}_{community_id}_{node}".encode(), digest_bits=256
        ).hexdigest(),
        "severity": FindingSeverity.Medium,
        "type": FindingType.Suspicious,
        "addresses": [node],
        "labels": [
            {
                "entity_type": EntityType.Address.value,
                "entity": node,
                "confidence": 90,
                "label": label,
            }
        ],
    }
    return alert_details


async def load_all_nodes_from_database(session):
    result = await session.execute(select(SybilClusters))
    existing_clusters = result.scalars().all()
    return {cluster.address: cluster for cluster in existing_clusters}


# async def store_graph_clusters(G, session):
#     identified_clusters = extract_clusters_from_graph(G)

#     for cluster in identified_clusters:
#         cluster_id = cluster["id"]
#         addresses = cluster[
#             "addresses"
#         ]  # This should be a list of addresses in the cluster

#         # Check if this cluster already exists in the database
#         existing_cluster = await session.execute(
#             select(SybilClusters).where(SybilClusters.cluster_id == str(cluster_id))
#         )

#         existing_cluster = existing_cluster.scalars().first()

#         if existing_cluster:
#             existing_addresses = (
#                 existing_cluster.address.split(",") if existing_cluster.address else []
#             )
#             existing_addresses.extend(addresses)
#             existing_cluster.address = ",".join(
#                 set(existing_addresses)
#             )  # remove duplicates
#         else:
#             new_cluster = SybilClusters(
#                 cluster_id=cluster_id,
#                 addresses=",".join(addresses),  # convert list to string
#                 creation_timestamp=datetime.datetime.utcnow(),
#                 last_update_timestamp=datetime.datetime.utcnow(),
#             )
#             session.add(new_cluster)

#         await session.commit()


# def extract_clusters_from_graph(G):
#     clusters = dict()

#     for node, data in G.nodes(data=True):
#         if "community" in data:  # Ensure that the node has a 'community' attribute
#             community_id = data["community"]
#             if community_id not in clusters:
#                 clusters[community_id] = {"id": community_id, "addresses": []}
#             clusters[community_id]["addresses"].append(node)

#     return list(clusters.values())
