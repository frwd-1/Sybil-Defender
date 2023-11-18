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

# Your README Title

## Comparison Example 1

<table>
  <tr>
    <td>
      <b>Feature A:</b> Description for feature A...
      <br>
      <img src="./images/SybilDefender_Cluster117.png" alt="Feature A">
    </td>
    <td>
      <b>Feature B:</b> Description for feature B...
      <br>
      <img src="./images/Cluster319.png" alt="Feature B">
    </td>
  </tr>
</table>

## Comparison Example 2

<table>
  <tr>
    <td>
      <b>Feature C:</b> Description for feature C...
      <br>
      <img src="path-to-image-for-feature-C.png" alt="Feature C">
    </td>
    <td>
      <b>Feature D:</b> Description for feature D...
      <br>
      <img src="path-to-image-for-feature-D.png" alt="Feature D">
    </td>
  </tr>
</table>

## Comparison Example 3

<table>
  <tr>
    <td>
      <b>Feature E:</b> Description for feature E...
      <br>
      <img src="path-to-image-for-feature-E.png" alt="Feature E">
    </td>
    <td>
      <b>Feature F:</b> Description for feature F...
      <br>
      <img src="path-to-image-for-feature-F.png" alt="Feature F">
    </td>
  </tr>
</table>

## Your Existing Comparison

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
      <img src="image-path-or-link" alt="Sybil Defender Cluster">
    </td>
  </tr>
</table>

Sybil Defender demonstrated a higher capability in identifying and visualizing complex clusters compared to Arbitrum's detection method.
