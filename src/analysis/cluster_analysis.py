# analysis.py
from src.analysis.base_detector import (
    AirdropFarmDetectorV1,
    AirdropFarmDetectorV2,
    SybilDetectionSystem,
)

# Placeholder configurations
config_v1 = {
    "threshold": 0.6,  # Arbitrary threshold value
    "patterns": ["DAI"],  # Example: look for DAI in transaction patterns
    "metadata": "Version 1 of the detector for airdrop farming",
}

config_v2 = {
    "threshold": 0.7,  # Another arbitrary threshold value
    "patterns": ["DAI", "USDC"],  # This version looks for DAI and USDC patterns
    "metadata": "Version 2 of the detector for airdrop farming",
}

detector_v1 = AirdropFarmDetectorV1(config_v1)
detector_v2 = AirdropFarmDetectorV2(config_v2)

system = SybilDetectionSystem([detector_v1, detector_v2])


def analyze_suspicious_clusters(suspicious_clusters):
    all_findings = []
    for cluster in suspicious_clusters:
        findings = system.analyze_cluster(cluster)
        all_findings.extend(findings)
    return all_findings
