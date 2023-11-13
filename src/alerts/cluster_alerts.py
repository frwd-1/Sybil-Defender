from Crypto.Hash import keccak
from forta_agent import Finding, FindingSeverity, FindingType, EntityType

import json


# def extract_addresses(entity):
#     # If the input is a string that looks like a list, we parse it.
#     if isinstance(entity, str) and entity.startswith("[") and entity.endswith("]"):
#         try:
#             # Safely parse the string as JSON, converting it to an actual list.
#             addresses = json.loads(entity)
#         except json.JSONDecodeError:
#             addresses = []
#     else:
#         addresses = [entity]

#     # Ensure each address is properly formatted (e.g., starts with "0x")
#     return [
#         format_address(address.strip())
#         for address in addresses
#         if isinstance(address, str)
#     ]


# def format_address(address):
#     """Ensure the Ethereum address starts with '0x' and is lower case."""
#     if not address.startswith("0x"):
#         return "0x" + address.lower()
#     return address.lower()


from Crypto.Hash import keccak  # Ensure to have the import statement for keccak


def generate_alert_details(community_id, nodes, labels, contracts, chainId, action):
    # Preparing metadata that includes details about the cluster and contracts.
    metadata = {
        "cluster_id": community_id,
        "chainId": chainId,
        "interacted_contracts": contracts,  # Directly using the list of contracts.
    }

    # Constructing labels for nodes, each enriched with metadata.
    labels_with_metadata = [
        {
            "entity_type": EntityType.Address,
            "entity": node,
            "confidence": 90,
            "label": label,
            "metadata": metadata,  # Attaching metadata to each node's label.
        }
        for node in nodes
        for label in labels  # Assuming each 'node' corresponds to every 'label' here.
    ]

    # Depending on the action, we set different alert names and descriptions.
    if action == "created":
        alert_name = "New sybil attack cluster identified"
        alert_description = f"Cluster {community_id} shows signs of sybil attack"
    else:  # For "updated" or any other action
        alert_name = "Existing sybil attack cluster updated"
        alert_description = (
            f"Cluster {community_id} has been updated with new activities"
        )

    # Assembling the final structure of the alert details.
    alert_details = {
        "name": alert_name,
        "description": alert_description,
        "alert_id": keccak.new(
            data=f"sybil_attacker_{community_id}".encode(), digest_bits=256
        ).hexdigest(),
        "severity": FindingSeverity.Medium,  # Assuming FindingSeverity is an enum, use the value.
        "type": FindingType.Suspicious,  # Assuming FindingType is an enum, use the value.
        "addresses": list(nodes),
        "labels": labels_with_metadata,  # Using the constructed labels with metadata.
    }

    return alert_details


# TODO: if there are updates to an existing cluster, generate an alert (ie, nodes added to cluster)
# TODO: 1. alert framework for cluster with similar transaction activity
# TODO: 2. alert framework for cluster transferring funds between x or more accounts
# TODO: alert should include contracts involved, suspected typology
