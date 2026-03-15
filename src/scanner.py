"""
WalletXpress - Multi-Chain Wallet Scanner
Scannt alle Balances auf Source-Wallets
"""

import yaml
from typing import Dict, List, Optional
from decimal import Decimal
from src.chains import TokenBalance, WalletScan, fetch_native_prices

class WalletScanner:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.min_value = Decimal(str(self.config['settings']['min_transfer_value']))
        self.enabled_chains = self.config['settings']['enabled_chains']
        
    def scan_all_wallets(self) -> Dict[str, List[WalletScan]]:
        """Scannt alle konfigurierten Source-Wallets"""
        results = {}

        # Native-Preise für alle aktiven Chains vorab laden (ein API-Call)
        fetch_native_prices(self.enabled_chains)

        for wallet_config in self.config['source_wallets']:
            wallet_address = wallet_config['address']
            wallet_name = wallet_config.get('name', 'Unnamed')

            print(f"\n🔍 Scanne {wallet_name} ({wallet_address[:6]}...{wallet_address[-4:]})")

            for chain in wallet_config['chains']:
                if chain not in self.enabled_chains:
                    continue

                print(f"  └─ Chain: {chain.upper()}", end=" ", flush=True)

                try:
                    scan_result = self.scan_wallet_on_chain(
                        wallet_name, wallet_address, chain
                    )
                    if scan_result:
                        results.setdefault(wallet_address, []).append(scan_result)
                        print(f"✅ ${scan_result.total_value_usd:.2f}")
                    else:
                        print("❌ Fehler")
                except Exception as e:
                    print(f"❌ {str(e)[:70]}")

        return results
    
    def scan_wallet_on_chain(self, wallet_name: str, address: str, chain: str) -> Optional[WalletScan]:
        """Scannt eine Wallet auf einer bestimmten Chain"""
        # Hier kommt die Chain-spezifische Logik
        # Wird von den Chain-Modulen implementiert
        from src.chains import get_chain_scanner
        
        scanner = get_chain_scanner(chain, self.config['rpc_endpoints'][chain])
        return scanner.scan(address, wallet_name, self.min_value)
    
    def calculate_transfer_plan(self, scans: Dict[str, List[WalletScan]]) -> Dict:
        """Erstellt einen Transfer-Plan basierend auf den Scans"""
        plan = {
            'total_wallets': len(scans),
            'total_chains': 0,
            'total_transfers': 0,
            'total_value_usd': Decimal('0'),
            'estimated_gas_cost_usd': Decimal('0'),
            'transfers': []
        }
        
        for address, chain_scans in scans.items():
            for scan in chain_scans:
                plan['total_chains'] += 1
                plan['total_value_usd'] += scan.total_value_usd
                
                # Native Token Transfer
                if scan.native_balance.value_usd and scan.native_balance.value_usd >= self.min_value:
                    plan['transfers'].append({
                        'from': address,
                        'to': self.config['target_wallet']['address'],
                        'chain': scan.chain,
                        'token': scan.native_balance.symbol,
                        'amount': scan.native_balance.balance,
                        'value_usd': scan.native_balance.value_usd
                    })
                    plan['total_transfers'] += 1
                
                # ERC-20 Token Transfers
                for token in scan.tokens:
                    if token.value_usd and token.value_usd >= self.min_value:
                        plan['transfers'].append({
                            'from': address,
                            'to': self.config['target_wallet']['address'],
                            'chain': scan.chain,
                            'token': token.symbol,
                            'token_address': token.address,
                            'amount': token.balance,
                            'value_usd': token.value_usd
                        })
                        plan['total_transfers'] += 1
        
        return plan
    
    def print_scan_summary(self, scans: Dict[str, List[WalletScan]]):
        """Gibt eine Zusammenfassung der Scans aus"""
        from tabulate import tabulate

        print("\n" + "="*80)
        print("📊 SCAN-ERGEBNIS")
        print("="*80)

        table_data = []
        total_value = Decimal('0')

        for address, chain_scans in scans.items():
            for scan in chain_scans:
                native = scan.native_balance
                token_str = ', '.join(
                    f"{t.symbol} ({t.balance:.4f})"
                    for t in scan.tokens if t.balance > 0
                ) or '-'
                table_data.append([
                    scan.wallet_name[:15],
                    scan.chain.upper(),
                    f"{native.balance:.4f} {native.symbol}",
                    f"${native.value_usd:.2f}" if native.value_usd else "$0.00",
                    token_str[:40],
                    f"${scan.total_value_usd:.2f}",
                ])
                total_value += scan.total_value_usd

        headers = ['Wallet', 'Chain', 'Native Balance', 'Native USD', 'Tokens', 'Gesamt USD']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print(f"\n💰 Gesamtwert aller Assets: ${total_value:.2f}")

if __name__ == "__main__":
    scanner = WalletScanner()
    results = scanner.scan_all_wallets()
    scanner.print_scan_summary(results)
