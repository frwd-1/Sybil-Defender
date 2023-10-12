from src.utils import globals

from src.database.models import SybilClusters
from src.database.db_utils import load_all_nodes_from_database

from src.database.db_controller import get_async_session
from src.alerts.cluster_alerts import generate_alert_details


from forta_agent import Finding


async def write_graph_to_database():
    findings = []

    async with get_async_session() as session:
        # Load all existing nodes from the database for comparison
        existing_nodes = await load_all_nodes_from_database(session)

        # Store updated clusters and their nodes
        updated_clusters = {}

        # Iterate and filter through graph nodes with 'label' attribute
        for node, data in globals.G1.nodes(data=True):
            if "label" in data:
                label = data["label"]
                community_id = data.get("community")

                # Convert interacting_contracts from list to string
                if "interacting_contracts" in data and isinstance(
                    data["interacting_contracts"], list
                ):
                    data["interacting_contracts"] = ",".join(
                        data["interacting_contracts"]
                    )

                # Check if node already exists
                existing_node = existing_nodes.get(node)

                # If new labeled node or label has changed, add to updated_clusters
                if not existing_node or existing_node.labels != label:
                    if community_id not in updated_clusters:
                        updated_clusters[community_id] = {
                            "nodes": set(),
                            "labels": set(),
                            "contracts": set(),
                        }
                    updated_clusters[community_id]["nodes"].add(node)
                    updated_clusters[community_id]["labels"].add(label)

                    # Update contracts; ensure we split the string back into a list for processing
                    updated_clusters[community_id]["contracts"].update(
                        data.get("interacting_contracts", "").split(",")
                    )

                    # Insert or update in database
                    new_cluster = SybilClusters(
                        cluster_id=str(community_id), address=node, labels=label
                    )
                    await session.merge(new_cluster)

        await session.commit()

        # Generate findings for updated clusters
        for community_id, data in updated_clusters.items():
            alert_details = generate_alert_details(
                community_id, data["nodes"], data["labels"], data["contracts"]
            )
            findings.append(Finding(alert_details))

    return findings


# TODO: generate the final graph based on the final database
