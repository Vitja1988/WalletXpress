# WalletXpress 💰

Multi-Chain Wallet-Konsolidierungs-Tool für automatischen Asset-Transfer zwischen eigenen Wallets.

## 🎯 Funktion

Scannt alle deine Wallets auf Multi-Chains, ermittelt alle Token-Balances und transferiert automatisch alles auf deine Haupt-Wallet - ohne manuelles Rumgefummel mit jeder Chain einzeln.

## ✨ Features

- **Multi-Chain Support**: ETH, BSC, Polygon, Arbitrum, Optimism, Avalanche, etc.
- **Auto-Token-Scanning**: Findet automatisch alle ERC-20/BEP-20/etc. Tokens auf deinen Wallets
- **Smart Routing**: Transferiert nur auf derselben Chain (kein teures Cross-Chain-Bridging)
- **Gas-Optimization**: Sammelt kleine Beträge und batcht Transfers wo möglich
- **Safety First**: Keine Keys in Klartext - verschlüsselte Key-Storage
- **Dry-Run Mode**: Simuliert Transfers vor dem echten Versand

## 🛠️ Architektur

```
WalletXpress/
├── src/
│   ├── chains/           # Chain-spezifische Module
│   │   ├── ethereum.py
│   │   ├── bsc.py
│   │   ├── polygon.py
│   │   └── ...
│   ├── scanner.py        # Wallet-Balance Scanner
│   ├── transfer.py       # Transfer-Logik
│   ├── gas_optimizer.py  # Gas-Kosten Optimierung
│   └── config.py         # Konfiguration
├── keys/                 # Verschlüsselte Key-Storage
├── tests/
└── requirements.txt
```

## ⚙️ Konfiguration

config.yaml:
```yaml
source_wallets:
  - address: "0x..."
    encrypted_key: "..."
    chains: ["eth", "bsc", "polygon"]
  
target_wallet:
  address: "0x..."
  
settings:
  min_transfer_value: 1.0  # USD - kleinere Beträge ignorieren
  max_gas_cost_percent: 5  # Max 5% Gas-Kosten vom Transfer-Wert
  dry_run: true            # Erst simulieren
```

## 🚀 Usage

```bash
# Scan alle Wallets (Dry-Run)
python walletxpress.py --scan

# Simuliere Transfers
python walletxpress.py --dry-run

# Echte Transfers
python walletxpress.py --execute
```

## 📝 Roadmap

- [ ] Phase 1: EVM-Chains (ETH, BSC, Polygon)
- [ ] Phase 2: Solana Support
- [ ] Phase 3: Bitcoin Support
- [ ] Phase 4: Cross-Chain Bridging (optional)

## ⚠️ Disclaimer

Nur für eigene Wallets! Verwendung auf fremde Wallets ist illegal.
