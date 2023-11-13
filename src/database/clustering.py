from src.utils import globals

from src.database.models import SybilClusters
from src.database.db_utils import load_all_nodes_from_database

from src.database.db_controller import get_async_session
from src.alerts.cluster_alerts import generate_alert_details


from forta_agent import Finding


# async def write_graph_to_database(final_graph, network_name):
#     print("Function 'write_graph_to_database' started.")
#     findings = []

#     async with get_async_session() as session:
#         print("Opened database session.")

#         # Fetch existing nodes and communities.
#         existing_nodes = await load_all_nodes_from_database(session)
#         print(f"Loaded {len(existing_nodes)} nodes from database.")

#         updated_clusters = {}
#         new_communities = set()

#         for node, data in final_graph.nodes(data=True):
#             print(f"Processing node: {node}")

#             if "label" in data:
#                 label = data["label"]
#                 community_id = data.get("community")
#                 print(f"Found label: {label}, community_id: {community_id}")

#                 existing_node = existing_nodes.get(node)

#                 if not existing_node:
#                     # Node doesn't exist, so this could be a new community or an update to an existing one.
#                     if community_id not in updated_clusters:
#                         # This is a new community or the first instance of an update to an existing community.
#                         updated_clusters[community_id] = {
#                             "nodes": set(),
#                             "labels": set(),
#                             "contracts": data.get("interacting_contracts", []),
#                             "chainId": network_name,  # Set chainId to network_name
#                         }
#                         # If the community_id doesn't exist in the database, it's a new community.
#                         if (
#                             community_id not in existing_nodes.values()
#                         ):  # Assuming existing_nodes.values() gives existing community_ids.
#                             new_communities.add(community_id)

#                     updated_clusters[community_id]["nodes"].add(node)
#                     updated_clusters[community_id]["labels"].add(label)
#                     # No need to update contracts here since we are not writing them to the database.

#                     new_cluster = SybilClusters(
#                         cluster_id=str(community_id),
#                         address=node,
#                         labels=label,
#                         chainId=network_name,  # Set chainId to network_name
#                     )
#                     await session.merge(new_cluster)
#                     print(f"Node {node} merged into session.")

#         await session.commit()
#         print("Session commit completed.")

#         for community_id, data in updated_clusters.items():
#             if community_id in new_communities:
#                 action = "created"
#             else:
#                 action = "updated"

#             # We are directly using the list of contracts for generating alert details.
#             alert_details = generate_alert_details(
#                 community_id,
#                 data["nodes"],
#                 data["labels"],
#                 data["contracts"],  # this is already a list
#                 action=action,
#             )
#             findings.append(Finding(alert_details))
#             print(f"Alert generated for {action} community: {community_id}")

#     print("Function 'write_graph_to_database' completed.")
#     return findings


# Assuming you have a way to access or pass the previous state of 'final_graph'
async def generate_alerts(analyzed_subgraph, previous_final_graph, network_name):
    print("Function 'generate_alerts' started.")
    findings = []

    updated_clusters = {}
    new_communities = set()

    for node, data in analyzed_subgraph.nodes(data=True):
        print(f"Processing node: {node}")

        if "label" in data:
            label = data["label"]
            community_id = data.get("community")
            print(f"Found label: {label}, community_id: {community_id}")

            # Check if this community ID has already been processed
            if community_id not in updated_clusters:
                # Assume the community is updated by default
                action = "updated"

                # Check if previous_final_graph is provided and not None
                if previous_final_graph:
                    # Check if this community exists in the previous graph
                    community_exists_in_previous = any(
                        community_id == node_data.get("community")
                        for _, node_data in previous_final_graph.nodes(data=True)
                    )

                    # If the community_id does not exist in the previous graph, it's a new community
                    if not community_exists_in_previous:
                        new_communities.add(community_id)
                        action = "created"

                # Initialize the community in updated_clusters
                updated_clusters[community_id] = {
                    "nodes": set(),
                    "labels": set(),
                    "contracts": data.get("interacting_contracts", []),
                    "chainId": network_name,
                    "action": action,  # Track the action for this community
                }

            # Add the current node to the community
            updated_clusters[community_id]["nodes"].add(node)
            updated_clusters[community_id]["labels"].add(label)

    # Generate alerts for new or updated communities
    for community_id, cluster_data in updated_clusters.items():
        alert_details = generate_alert_details(
            community_id,
            cluster_data["nodes"],
            cluster_data["labels"],
            cluster_data["contracts"],
            cluster_data["chainId"],
            action=cluster_data["action"],
        )
        findings.append(Finding(alert_details))
        print(f"Alert generated for {cluster_data['action']} community: {community_id}")

    print("Function 'generate_alerts' completed.")
    return findings


# TODO: generate the final graph based on the final database
