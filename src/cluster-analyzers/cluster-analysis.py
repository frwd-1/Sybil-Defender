def is_airdrop_farming(cluster):
    # This is a basic heuristic, it can be further refined based on real data.

    # Check the transaction pattern for sequential transfers
    sequential_transfers = True
    last_receiver = None
    for transaction in cluster:
        if last_receiver and last_receiver != transaction.sender:
            sequential_transfers = False
            break
        last_receiver = transaction.receiver

    # Check for back and forth conversions (ETH to DAI and DAI to ETH)
    # This is a simplification and in a real-world scenario would involve checking contract calls and tokens.
    conversion_count = sum(
        1
        for transaction in cluster
        if "DAI" in [transaction.sender, transaction.receiver]
    )

    return sequential_transfers and conversion_count > len(cluster) * 0.5


def analyze_cluster(cluster):
    if is_airdrop_farming(cluster):
        # Create an alert
        alert_details = {
            "name": "Potential Airdrop Farming",
            "description": "Sequential transfers and token conversions detected",
            "alert_id": keccak256(
                cluster[0].hash
            ),  # Just an example, this should be unique
            "severity": FindingSeverity.Medium.value,
            "type": FindingType.Suspicious.value,
            "addresses": [transaction.sender for transaction in cluster],
            "labels": [
                {
                    "entity_type": EntityType.Address.value,
                    "entity": transaction.sender,
                    "confidence": 90,
                    "label": "airdrop_farming",
                }
                for transaction in cluster
            ],
        }
        alert = Finding(alert_details)

        # Use Forta SDK's utility to send the alert
        # This is just a conceptual step, you'll need to integrate with Forta's sending mechanism.
        # send_alert(alert)
