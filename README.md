# Sybil Defender Bot for Forta Network

## Overview

Sybil Defender is a Forta bot developed to identify Sybil attacks on the application layer of EVM-compatible blockchains. This includes Ethereum, Arbitrum, Optimism, Polygon, Binance Smart Chain, Avalanche, and Fantom. It monitors transactions to detect patterns that may indicate Sybil behavior, such as Airdrop Farming, Governance Attacks, and Wash Trading/Market Manipulation.

## Features

- **Transaction Monitoring:** Monitors on-chain transactions for potential Sybil activities.
- **Heuristic Analysis:** Applies heuristics to initially assess transactions for Sybil attack patterns.
- **Graph Building:** Constructs directed subgraphs from transactions to analyze wallet clusters.
- **Community Detection:** Employs algorithms to identify potential Sybil communities.
- **Anomaly Alerting:** Alerts on unusual transaction patterns and interactions.
- **State Persistence:** Keeps track of historical data for ongoing analysis.

## Performance Comparison

A performance comparison was conducted between Sybil Defender and Arbitrum's Sybil detection mechanisms.

- **Arbitrum Detection:** Detected a cluster with 56 addresses for node `0xc7bb9b943fd2a04f651cc513c17eb5671b90912d`.

![Arbitrum Cluster](image-path-or-link)

- **Sybil Defender Detection:** Detected a more complex cluster with 96 addresses for the same node.

![Sybil Defender Cluster](image-path-or-link)

Sybil Defender demonstrated a higher capability in identifying and visualizing complex clusters compared to Arbitrum's detection method.

## Contributing

Contributors are encouraged to submit pull requests to improve the bot. Please adhere to the code style and guidelines provided.

## License

Sybil Defender is made available under the MIT License.

---

Please note that the images are for demonstration purposes. Replace `image-path-or-link` with the actual paths or URLs to the images in your repository.
