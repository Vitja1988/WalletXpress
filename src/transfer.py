"""
WalletXpress - Transfer Execution
Führt die tatsächlichen Transfers durch
"""

import yaml
from decimal import Decimal
from typing import Dict, List
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account
import time

@dataclass
class Transfer:
    from_wallet: str
    to_wallet: str
    chain: str
    token: str
    token_address: str  # "native" für ETH/BNB/etc.
    amount: Decimal
    value_usd: Decimal
    
class TransferExecutor:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.dry_run = self.config['settings']['dry_run']
        self.max_gas_percent = self.config['settings']['max_gas_cost_percent']
        
    def execute_transfers(self, transfers: List[Transfer]):
        """Führt alle Transfers aus"""
        print(f"\n{'='*80}")
        print(f"🚀 TRANSFER-EXECUTION")
        print(f"{'='*80}")
        print(f"Dry-Run: {self.dry_run}")
        print(f"Anzahl Transfers: {len(transfers)}")
        
        results = []
        
        for i, tx in enumerate(transfers, 1):
            print(f"\n[{i}/{len(transfers)}] {tx.token} auf {tx.chain.upper()}")
            print(f"   Von: {tx.from_wallet[:10]}...")
            print(f"   Nach: {tx.to_wallet[:10]}...")
            print(f"   Menge: {tx.amount:.6f} {tx.token}")
            print(f"   Wert: ~${tx.value_usd:.2f}")
            
            if self.dry_run:
                print("   ⏸️  DRY-RUN - Kein echter Transfer")
                results.append({'status': 'dry_run', 'transfer': tx})
            else:
                result = self._execute_single_transfer(tx)
                results.append(result)
                
                # Kurze Pause zwischen Transfers
                if i < len(transfers):
                    time.sleep(2)
        
        return results
    
    def _execute_single_transfer(self, tx: Transfer) -> Dict:
        """Führt einen einzelnen Transfer aus"""
        try:
            from src.chains import get_chain_scanner
            
            rpc = self.config['rpc_endpoints'][tx.chain]
            scanner = get_chain_scanner(tx.chain, rpc)
            w3 = scanner.w3
            
            # Private Key holen (verschlüsselt gespeichert)
            private_key = self._get_private_key(tx.from_wallet)
            account = Account.from_key(private_key)
            
            if tx.token_address == "native":
                # Native Token Transfer (ETH, BNB, etc.)
                tx_hash = self._send_native(w3, account, tx)
            else:
                # ERC-20 Token Transfer
                tx_hash = self._send_token(w3, account, tx)
            
            print(f"   ✅ Erfolg! TX: {tx_hash[:20]}...")
            return {'status': 'success', 'tx_hash': tx_hash, 'transfer': tx}
            
        except Exception as e:
            print(f"   ❌ Fehler: {str(e)[:60]}")
            return {'status': 'error', 'error': str(e), 'transfer': tx}
    
    def _send_native(self, w3: Web3, account: Account, tx: Transfer) -> str:
        """Sendet Native Token"""
        # Gas-Preis holen
        gas_price = w3.eth.gas_price
        
        # Transaction bauen
        transaction = {
            'nonce': w3.eth.get_transaction_count(account.address),
            'gasPrice': gas_price,
            'gas': 21000,  # Standard für Simple Transfer
            'to': w3.to_checksum_address(tx.to_wallet),
            'value': w3.to_wei(tx.amount, 'ether'),
            'chainId': w3.eth.chain_id,
        }
        
        # Signieren & Senden
        signed = w3.eth.account.sign_transaction(transaction, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        
        return tx_hash.hex()
    
    def _send_token(self, w3: Web3, account: Account, tx: Transfer) -> str:
        """Sendet ERC-20 Token"""
        from src.chains import EVMChainScanner
        
        token_contract = w3.eth.contract(
            address=w3.to_checksum_address(tx.token_address),
            abi=EVMChainScanner.ERC20_ABI
        )
        
        # Token-Transfer-Funktion
        decimals = token_contract.functions.decimals().call()
        amount_raw = int(tx.amount * (10 ** decimals))
        
        # Transaction bauen
        txn = token_contract.functions.transfer(
            w3.to_checksum_address(tx.to_wallet),
            amount_raw
        ).buildTransaction({
            'nonce': w3.eth.get_transaction_count(account.address),
            'gasPrice': w3.eth.gas_price,
            'gas': 100000,  # ERC-20 Transfer braucht mehr Gas
            'chainId': w3.eth.chain_id,
        })
        
        # Signieren & Senden
        signed = w3.eth.account.sign_transaction(txn, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        
        return tx_hash.hex()
    
    def _get_private_key(self, address: str) -> str:
        """Holt den entschlüsselten Private Key für eine Adresse"""
        # TODO: Implementiere echte Verschlüsselung
        # Für jetzt: Dummy-Implementierung
        for wallet in self.config['source_wallets']:
            if wallet['address'].lower() == address.lower():
                # Hier würde Entschlüsselung stattfinden
                return "PRIVATE_KEY_PLACEHOLDER"
        raise ValueError(f"Kein Key für Adresse {address} gefunden")

if __name__ == "__main__":
    executor = TransferExecutor()
    # Beispiel-Transfers
    test_transfers = [
        Transfer(
            from_wallet="0x...",
            to_wallet="0x...",
            chain="ethereum",
            token="ETH",
            token_address="native",
            amount=Decimal("0.1"),
            value_usd=Decimal("200")
        )
    ]
    executor.execute_transfers(test_transfers)
