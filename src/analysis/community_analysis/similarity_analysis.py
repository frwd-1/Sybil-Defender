from collections import defaultdict
from src.database.db_controller import get_async_session
from src.database.models import SybilClusters
from src.utils import globals
from src.utils.constants import INTERACTION_RATIO, SIMILARITY_THRESHOLD
from sqlalchemy.future import select
from src.database.models import (
    ContractTransaction,
)
from src.analysis.transaction_analysis.helpers import (
    get_unique_senders,
    compute_similarity,
    build_contract_activity_dict,
)

from forta_agent import Finding, FindingSeverity, FindingType, EntityType
from Crypto.Hash import keccak


async def group_addresses_by_community():
    grouped_addresses = defaultdict(set)
    for node, data in globals.G1.nodes(data=True):
        community_id = data["community"]
        grouped_addresses[community_id].add(node)
    return grouped_addresses


async def similarity_analysis():
    grouped_addresses = await group_addresses_by_community()

    # communities_to_remove = set()
    findings = []
    async with get_async_session() as session:
        for community_id, addresses in grouped_addresses.items():
            result2 = await session.execute(
                select(ContractTransaction)
                .where(ContractTransaction.sender.in_(addresses))
                .order_by(ContractTransaction.timestamp)
            )
            contract_transactions = result2.scalars().all()

            unique_senders = await get_unique_senders(contract_transactions)

            if len(unique_senders) < len(addresses) * INTERACTION_RATIO:
                # communities_to_remove.add(community_id)
                continue

            contract_activity_dict = await build_contract_activity_dict(
                contract_transactions
            )
            avg_similarity = await compute_similarity(addresses, contract_activity_dict)

            if avg_similarity >= SIMILARITY_THRESHOLD:
                # Step 1: Label cluster in graph's metadata
                for address in addresses:
                    globals.G1.nodes[address]["label"] = "sybil airdrop farmer"
                    globals.G1.nodes[address][
                        "typology"
                    ] = "similar contract interaction pattern"

                # Step 2: Generate Finding
                interacting_contracts = {
                    tx.contract_address for tx in contract_transactions
                }  # Extract the contracts the cluster interacts with
                alert_details = {
                    "name": "Sybil Airdrop Farmer Detected",
                    "description": f"Cluster {community_id} shows signs of sybil airdrop farming with average similarity of {avg_similarity}",
                    "alert_id": keccak.new(
                        data=f"sybil_airdrop_farmer_{community_id}".encode(),
                        digest_bits=256,
                    ).hexdigest(),
                    "severity": FindingSeverity.Medium,
                    "type": FindingType.Suspicious,
                    "addresses": list(addresses),
                    "labels": [
                        {
                            "entity_type": EntityType.Address.value,
                            "entity": address,
                            "confidence": 90,
                            "label": "sybil_airdrop_farming",
                        }
                        for address in addresses
                    ]
                    + [
                        {
                            "entity_type": EntityType.Address.value,
                            "entity": contract,
                            "confidence": 90,
                            "label": "interacted_by_sybil",
                        }
                        for contract in interacting_contracts
                    ],
                }
                findings.append(Finding(alert_details))

                # Step 3: Add Cluster to Sybil Clusters Table

                for address in addresses:
                    sybil_cluster = SybilClusters(
                        cluster_id=str(community_id),
                        address=address,
                    )
                    session.add(sybil_cluster)
                await session.commit()

    return findings
