# Sybil Defender

## Overview

Sybil Defender is a Forta bot developed to identify Sybil attacks on the application layer of EVM-compatible blockchains. This includes Ethereum, Arbitrum, Optimism, Polygon, Binance Smart Chain, Avalanche, and Fantom. It monitors transactions to detect patterns that may indicate Sybil behavior, such as Airdrop Farming, Governance Attacks, and Wash Trading/Market Manipulation.

## Features

- **Transaction Monitoring:** Monitors on-chain transactions for potential Sybil activities.
- **Heuristic Analysis:** Applies heuristics to initially assess transactions for Sybil attack patterns.
- **Graph Building:** Constructs directed subgraphs from transactions to analyze wallet clusters.
- **Community Detection:** Employs algorithms to identify potential Sybil communities.
- **Anomaly Alerting:** Alerts on unusual transaction patterns and interactions.
- **State Persistence:** Keeps track of historical data for dynamic clustering and real-time analysis.

## Performance Comparison

A performance comparison was conducted between Sybil Defender and Arbitrum's Sybil detection mechanisms.

<table>
  <tr>
    <td>
      <b>Arbitrum Detection:</b> Detected a cluster with 56 addresses for node <code>0xc7bb9b943fd2a04f651cc513c17eb5671b90912d</code>.
      <br>
      <img src="./images/Cluster1544.png" alt="Arbitrum Cluster">
    </td>
    <td>
      <b>Sybil Defender Detection:</b> Detected a more complex cluster with 96 addresses for the same node.
      <br>
      <img src="./images/SybilDefender_Cluster82.png" alt="Sybil Defender Cluster">
    </td>
  </tr>
</table>

Sybil Defender demonstrated a higher capability in identifying and visualizing complex clusters compared to Arbitrum's detection method.
