from Crypto.Hash import keccak
from forta_agent import Finding, FindingSeverity, FindingType, EntityType


def generate_alert_details(community_id, nodes, labels, contracts):
    alert_details = {
        "name": "Sybil asset farmer detected",
        "description": f"Cluster {community_id} shows signs of sybil asset farming",
        "alert_id": keccak.new(
            data=f"sybil_asset_farmer_{community_id}".encode(),
            digest_bits=256,
        ).hexdigest(),
        "severity": FindingSeverity.Medium,
        "type": FindingType.Suspicious,
        "addresses": list(nodes),
        "labels": [
            {
                "entity_type": EntityType.Address.value,
                "entity": node,
                "confidence": 90,
                "label": label,
            }
            for node in nodes
            for label in labels
        ]
        + [
            {
                "entity_type": EntityType.Address.value,
                "entity": contract,
                "confidence": 90,
                "label": "interacted_by_sybil",
            }
            for contract in contracts
        ],
    }
    return alert_details


# TODO: if there are updates to an existing cluster, generate an alert (ie, nodes added to cluster)
# TODO: 1. alert framework for cluster with similar transaction activity
# TODO: 2. alert framework for cluster transferring funds between x or more accounts
# TODO: alert should include contracts involved, suspected typology
