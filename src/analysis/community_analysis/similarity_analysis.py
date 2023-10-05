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
                continue

            contract_activity_dict = await build_contract_activity_dict(
                contract_transactions
            )
            avg_similarity = await compute_similarity(addresses, contract_activity_dict)

            if avg_similarity >= SIMILARITY_THRESHOLD:
                for address in addresses:
                    globals.G1.nodes[address]["label"] = "sybil airdrop farmer"
                    globals.G1.nodes[address][
                        "typology"
                    ] = "similar contract interaction pattern"

                interacting_contracts = {
                    tx.contract_address for tx in contract_transactions
                }
                interacting_contracts_list = list(interacting_contracts)
                # TODO: add the functionality that adds contracts as nodes
                for address in addresses:
                    globals.G1.nodes[address][
                        "interacting_contracts"
                    ] = interacting_contracts_list
