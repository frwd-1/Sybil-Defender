# detectors.py
from forta_agent import Finding, FindingSeverity, FindingType, EntityType
from Crypto.Hash import keccak


class BaseDetector:
    def __init__(self, config):
        self.config = config

    def detect(self, _):
        raise NotImplementedError("Subclasses should implement this!")

    def send_alert(self, alert_details):
        finding = Finding(alert_details)
        return finding


class AirdropFarmDetectorV1(BaseDetector):
    def detect(self, cluster):
        findings = []
        if self.is_airdrop_farming_v1(cluster):
            alert_details = {
                "name": "Potential Airdrop Farming v1",
                "description": "Sequential transfers and token conversions detected v1",
                "alert_id": keccak(cluster[0].hash),
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
            findings.append(self.send_alert(alert_details))
        return findings

    def is_airdrop_farming_v1(self, cluster):
        # Placeholder: Detect if more than half the transactions involve the configured pattern
        return (
            sum(
                1
                for transaction in cluster
                if self.config["patterns"][0]
                in [transaction.sender, transaction.receiver]
            )
            > len(cluster) * self.config["threshold"]
        )


class AirdropFarmDetectorV2(BaseDetector):
    def detect(self, cluster):
        findings = []
        if self.is_airdrop_farming_v2(cluster):
            alert_details = {
                "name": "Potential Airdrop Farming v2",
                "description": "Sequential transfers and token conversions detected v2",
                "alert_id": keccak(cluster[0].hash),
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
            findings.append(self.send_alert(alert_details))
        return findings

    def is_airdrop_farming_v2(self, cluster):
        # Placeholder: Detect if more than half the transactions involve any of the configured patterns
        pattern_count = sum(
            1
            for transaction in cluster
            for pattern in self.config["patterns"]
            if pattern in [transaction.sender, transaction.receiver]
        )
        return pattern_count > len(cluster) * self.config["threshold"]


class SybilDetectionSystem:
    def __init__(self, detectors):
        self.detectors = detectors

    def analyze_cluster(self, cluster):
        findings = []
        for detector in self.detectors:
            findings.extend(detector.detect(cluster))
        return findings
