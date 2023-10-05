from src.analysis.community_analysis.similarity_analysis import (
    similarity_analysis,
)


async def analyze_suspicious_clusters():
    await similarity_analysis()
