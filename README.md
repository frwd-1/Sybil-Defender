# Sybil Defender

## Overview

The Sybil Defender identifies and labels Sybil Attack clusters operating on the application layer of EVM-compatible blockchains. This includes Ethereum, Arbitrum, Optimism, Polygon, Binance Smart Chain, Avalanche, and Fantom. It monitors transactions to detect patterns that may indicate Sybil behavior, such as Airdrop Farming, Governance Attacks, and Wash Trading/Market Manipulation.

## Features

- **Real Time Monitoring:** Monitors on-chain transactions in real time.
- **Dynamic Clustering:** Dynamically updates existing clusters based on incoming activity.
- **Heuristic Analysis:** Applies heuristics to initially assess transactions for Sybil attack patterns.
- **Community Detection:** Employs sophisticated algorithms to identify communities.
- **Sybil Detection:** Filters communities for known Sybil Attack patterns to generate accurate alerts.
- **State Persistence:** Keeps track of historical data for dynamic clustering and real-time analysis.

## Performance

During a performance evaluation, Sybil Defender analyzed a sample of approximately 8 hours of activity on the Arbitrum network prior to the airdrop snapshot in March 2023. The analysis identified 211 Sybil Clusters consisting of 7731 nodes in total.

In addition, this evaluation confirmed the identification of all 4 clusters previously detected by Arbitrum's Sybil detection mechanisms.

## Sample 1

<table>
  <tr>
    <td>
      <b>Sybil Defender:</b> Identified Sybil cluster with 95 eligible nodes
      <br>
      <img src="./images/SybilDefender_Cluster117.png" width="300" height="200">
    </td>
    <td>
      <b>Arbitrum Detection:</b> Identified Sybil cluster with 56 eligible nodes
      <br>
      <img src="./images/Cluster1544.png" width="300" height="200">
    </td>
  </tr>
  <tr>
    <td colspan="2" style="text-align:center;">
      Common address: 0xc7bb9b943fd2a04f651cc513c17eb5671b90912d
    </td>
  </tr>
</table>

## Sample 2

<table>
  <tr>
    <td>
      <b>Sybil Defender:</b> Identified Sybil cluster with 99 eligible nodes
      <br>
      <img src="./images/SybilDefender_Cluster82.png" alt="Sybil Defender Cluster" width="300" height="200">
    </td>
    <td>
      <b>Arbitrum Detection:</b> Identified Sybil cluster with 110 eligible nodes
      <br>
      <img src="./images/Cluster319.png" alt="Arbitrum Cluster" width="300" height="200">
    </td>
  </tr>
  <tr>
    <td colspan="2" style="text-align:center;">
      Common address: 0x1ddbf60792aac896aed180eaa6810fccd7839ada
    </td>
  </tr>
</table>

## Sample 3

<table>
  <tr>
    <td>
      <b>Sybil Defender:</b> Identified Sybil cluster with 507 eligible nodes
      <br>
      <img src="./images/Cluster3.png" alt="Sybil Defender Cluster" width="300" height="200">
    </td>
    <td>
      <b>Arbitrum Detection:</b> Identified Sybil cluster with 121 eligible nodes
      <br>
      <img src="./images/Cluster2554.png" alt="Arbitrum Cluster" width="300" height="200">
    </td>
  </tr>
  <tr>
    <td colspan="2" style="text-align:center;">
      Common address: 0x3fb4c01b5ceecf307010f84c9a858aeaeab0b9fa
    </td>
  </tr>
</table>

## Sample 4

<table>
  <tr>
    <td>
      <b>Sybil Defender:</b> Identified Sybil cluster with 51 eligible nodes
      <br>
      <img src="./images/Cluster85.png" alt="Sybil Defender Cluster" width="300" height="200">
    </td>
    <td>
      <b>Arbitrum Detection:</b> Identified Sybil cluster with 65 eligible nodes
      <br>
      <img src="./images/Cluster3316.png" alt="Arbitrum Cluster" width="300" height="200">
    </td>
  </tr>
  <tr>
    <td colspan="2" style="text-align:center;">
      Common address: 0x15bc18bb8c378c94c04795d72621957497130400
    </td>
  </tr>
</table>

The full sample graph file is [here](src/tests/ArbitrumSampling.graphml).
