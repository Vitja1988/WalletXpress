"""
Chain-Scanner Factory
Liefert den passenden Scanner für jede Chain
"""

from typing import Dict, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from web3 import Web3
import requests

@dataclass
class TokenBalance:
    symbol: str
    address: str
    balance: Decimal
    decimals: int
    value_usd: Decimal = None

@dataclass
class WalletScan:
    wallet_name: str
    address: str
    chain: str
    native_balance: TokenBalance
    tokens: list
    total_value_usd: Decimal

class BaseChainScanner(ABC):
    def __init__(self, rpc_url: str, chain_id: int, native_symbol: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.chain_id = chain_id
        self.native_symbol = native_symbol
        
    @abstractmethod
    def scan(self, address: str, wallet_name: str, min_value: Decimal) -> WalletScan:
        pass
    
    def get_native_balance(self, address: str) -> TokenBalance:
        """Holt den Native-Token-Balance (ETH, BNB, MATIC, etc.)"""
        balance_wei = self.w3.eth.get_balance(address)
        balance_eth = Decimal(self.w3.from_wei(balance_wei, 'ether'))
        
        return TokenBalance(
            symbol=self.native_symbol,
            address="native",
            balance=balance_eth,
            decimals=18
        )
    
    def get_token_price(self, token_address: str, chain: str) -> Decimal:
        """Holt Token-Preis in USD (z.B. von CoinGecko oder DexScreener)"""
        # Platzhalter - hier würde echte Preis-API kommen
        # Für jetzt: Dummy-Implementierung
        return Decimal('0')

class EVMChainScanner(BaseChainScanner):
    """Scanner für EVM-basierte Chains (ETH, BSC, Polygon, etc.)"""
    
    # Standard ERC-20 ABI für balanceOf
    ERC20_ABI = '''[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"}]'''
    
    # Bekannte Token-Listen pro Chain (können erweitert werden)
    KNOWN_TOKENS = {
        'ethereum': {
            'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
        },
        'bsc': {
            'USDT': '0x55d398326f99059fF775485246999027B3197955',
            'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
            'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
            'DAI': '0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3',
        },
        'polygon': {
            'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
            'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
            'DAI': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
            'WBTC': '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
        },
    }
    
    def __init__(self, rpc_url: str, chain_id: int, native_symbol: str, chain_name: str):
        super().__init__(rpc_url, chain_id, native_symbol)
        self.chain_name = chain_name
    
    def scan(self, address: str, wallet_name: str, min_value: Decimal) -> WalletScan:
        """Scannt eine EVM-Wallet"""
        checksum_addr = self.w3.to_checksum_address(address)
        
        # Native Balance
        native = self.get_native_balance(checksum_addr)
        
        # Token Balances
        tokens = []
        known = self.KNOWN_TOKENS.get(self.chain_name, {})
        
        for symbol, token_addr in known.items():
            try:
                balance = self.get_token_balance(checksum_addr, token_addr)
                if balance.balance > 0:
                    tokens.append(balance)
            except Exception as e:
                print(f"    ⚠️  {symbol}: {e}")
        
        # Berechne Gesamtwert (ohne echte Preise für jetzt)
        total_value = Decimal('0')  # Würde mit echten Preisen berechnet
        
        return WalletScan(
            wallet_name=wallet_name,
            address=address,
            chain=self.chain_name,
            native_balance=native,
            tokens=tokens,
            total_value_usd=total_value
        )
    
    def get_token_balance(self, wallet_address: str, token_address: str) -> TokenBalance:
        """Holt ERC-20 Token Balance"""
        token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(token_address),
            abi=self.ERC20_ABI
        )
        
        symbol = token_contract.functions.symbol().call()
        decimals = token_contract.functions.decimals().call()
        balance = token_contract.functions.balanceOf(wallet_address).call()
        
        balance_decimal = Decimal(balance) / (Decimal(10) ** decimals)
        
        return TokenBalance(
            symbol=symbol,
            address=token_address,
            balance=balance_decimal,
            decimals=decimals
        )

def get_chain_scanner(chain: str, rpc_url: str):
    """Factory-Funktion - liefert den passenden Scanner"""
    
    chain_configs = {
        'ethereum': (1, 'ETH', 'ethereum'),
        'bsc': (56, 'BNB', 'bsc'),
        'polygon': (137, 'MATIC', 'polygon'),
        'arbitrum': (42161, 'ETH', 'arbitrum'),
        'optimism': (10, 'ETH', 'optimism'),
        'avalanche': (43114, 'AVAX', 'avalanche'),
        'base': (8453, 'ETH', 'base'),
    }
    
    if chain not in chain_configs:
        raise ValueError(f"Unbekannte Chain: {chain}")
    
    chain_id, symbol, name = chain_configs[chain]
    return EVMChainScanner(rpc_url, chain_id, symbol, name)
