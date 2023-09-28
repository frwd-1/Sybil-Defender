from collections import defaultdict
from src.analysis.helpers import jaccard_similarity, extract_activity_pairs
from src.database.db_controller import get_async_session, initialize_database
from src.utils import globals
from src.utils.constants import INTERACTION_RATIO, SIMILARITY_THRESHOLD
from sqlalchemy.future import select
from src.database.models import (
    ContractTransaction,
)
from .helpers import (
    get_unique_senders,
    compute_similarity,
    build_contract_activity_dict,
    add_contract_transactions_to_graph,
)


async def group_addresses_by_community():
    grouped_addresses = defaultdict(set)
    for node, data in globals.G1.nodes(data=True):
        community_id = data["community"]
        grouped_addresses[community_id].add(node)
    return grouped_addresses


async def analyze_communities(grouped_addresses):
    communities_to_remove = set()
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
                communities_to_remove.add(community_id)
                continue

            contract_activity_dict = await build_contract_activity_dict(
                contract_transactions
            )
            avg_similarity = await compute_similarity(addresses, contract_activity_dict)

            if avg_similarity >= SIMILARITY_THRESHOLD:
                await add_contract_transactions_to_graph(
                    contract_transactions, community_id
                )
            else:
                communities_to_remove.add(community_id)

    return communities_to_remove
