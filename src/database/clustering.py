from src.utils import globals

from src.database.models import SybilClusters
from src.database.db_utils import load_all_nodes_from_database

from src.database.db_controller import get_async_session
from src.alerts.cluster_alerts import generate_alert_details


from forta_agent import Finding


import asyncio


async def write_graph_to_database(final_graph):
    print("Function 'write_graph_to_database' started.")
    findings = []

    async with get_async_session() as session:
        print("Opened database session.")

        # Fetch existing nodes and communities.
        existing_nodes = await load_all_nodes_from_database(session)
        print(f"Loaded {len(existing_nodes)} nodes from database.")

        updated_clusters = {}
        new_communities = set()

        for node, data in final_graph.nodes(data=True):
            print(f"Processing node: {node}")

            if "label" in data:
                label = data["label"]
                community_id = data.get("community")
                print(f"Found label: {label}, community_id: {community_id}")

                # Removed the code that modifies "interacting_contracts"

                existing_node = existing_nodes.get(node)

                if not existing_node:
                    # Node doesn't exist, so this could be a new community or an update to an existing one.
                    if community_id not in updated_clusters:
                        # This is a new community or the first instance of an update to an existing community.
                        updated_clusters[community_id] = {
                            "nodes": set(),
                            "labels": set(),
                            # We will keep contracts as lists in the updated clusters.
                            "contracts": data.get(
                                "interacting_contracts", []
                            ),  # Directly using the list
                        }
                        # If the community_id doesn't exist in the database, it's a new community.
                        if (
                            community_id not in existing_nodes.values()
                        ):  # Assuming existing_nodes.values() gives existing community_ids.
                            new_communities.add(community_id)

                    updated_clusters[community_id]["nodes"].add(node)
                    updated_clusters[community_id]["labels"].add(label)
                    # No need to update contracts here since we are not writing them to the database.

                    new_cluster = SybilClusters(
                        cluster_id=str(community_id), address=node, labels=label
                    )
                    await session.merge(new_cluster)
                    print(f"Node {node} merged into session.")

        await session.commit()
        print("Session commit completed.")

        for community_id, data in updated_clusters.items():
            if community_id in new_communities:
                action = "created"
            else:
                action = "updated"

            # We are directly using the list of contracts for generating alert details.
            alert_details = generate_alert_details(
                community_id,
                data["nodes"],
                data["labels"],
                data["contracts"],  # this is already a list
                action=action,
            )
            findings.append(Finding(alert_details))
            print(f"Alert generated for {action} community: {community_id}")

    print("Function 'write_graph_to_database' completed.")
    return findings


# TODO: generate the final graph based on the final database
