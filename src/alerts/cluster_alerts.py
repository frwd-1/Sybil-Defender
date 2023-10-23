from Crypto.Hash import keccak
from forta_agent import Finding, FindingSeverity, FindingType, EntityType

import json


def extract_addresses(entity):
    # Remove leading/trailing whitespaces and the characters "[", "]"
    cleaned_string = entity.strip().strip("[").strip("]").replace('"', "")

    # Split the addresses based on comma separation
    addresses = cleaned_string.split(",")

    # Ensure each address is properly formatted (e.g., starts with "0x")
    return [format_address(address.strip()) for address in addresses]


def format_address(address):
    """Ensure the Ethereum address starts with '0x'."""
    if not address.startswith("0x"):
        return "0x" + address
    return address


def generate_alert_details(community_id, nodes, labels, contracts, action):
    # Preparing metadata that includes details about the cluster and contracts.
    if contracts and isinstance(contracts, str):
        # Assuming 'contracts' is the string containing the list representation
        contracts = extract_addresses(contracts)

    metadata = {
        "cluster_id": community_id,
        "interacted_contracts": list(
            contracts
        ),  # Contracts are now only listed in the metadata.
    }

    # Constructing labels for nodes, each enriched with metadata.
    labels_with_metadata = [
        {
            "entity_type": EntityType.Address.value,
            "entity": node,
            "confidence": 90,
            "label": label,
            "metadata": metadata,  # Attaching metadata to each node's label.
        }
        for node in nodes
        for label in labels
    ]

    # Depending on the action, we set different alert names and descriptions.
    if action == "created":
        alert_name = "New sybil asset farmer detected"
        alert_description = f"Cluster {community_id} shows signs of sybil asset farming"
    else:  # For "updated" or any other action
        alert_name = "Existing sybil cluster updated"
        alert_description = (
            f"Cluster {community_id} has been updated with new activities"
        )

    # Assembling the final structure of the alert details.
    alert_details = {
        "name": alert_name,
        "description": alert_description,
        "alert_id": keccak.new(
            data=f"sybil_asset_farmer_{community_id}".encode(), digest_bits=256
        ).hexdigest(),
        "severity": FindingSeverity.High,
        "type": FindingType.Suspicious,
        "addresses": list(nodes),
        "labels": labels_with_metadata,  # Using the constructed labels with metadata.
    }

    return alert_details


# TODO: if there are updates to an existing cluster, generate an alert (ie, nodes added to cluster)
# TODO: 1. alert framework for cluster with similar transaction activity
# TODO: 2. alert framework for cluster transferring funds between x or more accounts
# TODO: alert should include contracts involved, suspected typology
