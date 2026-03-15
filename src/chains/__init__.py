"""
Chain-Scanner Factory
Liefert den passenden Scanner für jede Chain
"""

from typing import Dict, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from web3 import Web3
import requests
import time

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

# CoinGecko IDs für native Token
NATIVE_COINGECKO_IDS = {
    'ethereum': 'ethereum',
    'bsc': 'binancecoin',
    'polygon': 'matic-network',
    'arbitrum': 'ethereum',
    'optimism': 'ethereum',
    'avalanche': 'avalanche-2',
    'base': 'ethereum',
}

# CoinGecko Platform-IDs für ERC-20 Token
COINGECKO_PLATFORMS = {
    'ethereum': 'ethereum',
    'bsc': 'binance-smart-chain',
    'polygon': 'polygon-pos',
    'arbitrum': 'arbitrum-one',
    'optimism': 'optimistic-ethereum',
    'avalanche': 'avalanche',
    'base': 'base',
}

# Einfacher In-Memory Cache (symbol/address → preis)
_price_cache: Dict[str, Decimal] = {}
_cache_time: Dict[str, float] = {}
CACHE_TTL = 300  # 5 Minuten

def _cached_price(key: str) -> Optional[Decimal]:
    if key in _price_cache and (time.time() - _cache_time.get(key, 0)) < CACHE_TTL:
        return _price_cache[key]
    return None

def _store_price(key: str, price: Decimal):
    _price_cache[key] = price
    _cache_time[key] = time.time()

def fetch_native_prices(chain_names: list) -> Dict[str, Decimal]:
    """Holt native Token-Preise für mehrere Chains auf einmal."""
    ids_needed = []
    for chain in chain_names:
        cg_id = NATIVE_COINGECKO_IDS.get(chain)
        if cg_id and _cached_price(cg_id) is None:
            ids_needed.append(cg_id)

    if ids_needed:
        try:
            ids_str = ','.join(set(ids_needed))
            resp = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={'ids': ids_str, 'vs_currencies': 'usd'},
                timeout=10
            )
            if resp.ok:
                data = resp.json()
                for cg_id, prices in data.items():
                    _store_price(cg_id, Decimal(str(prices.get('usd', 0))))
        except Exception:
            pass

    result = {}
    for chain in chain_names:
        cg_id = NATIVE_COINGECKO_IDS.get(chain)
        result[chain] = _cached_price(cg_id) or Decimal('0')
    return result


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
        balance_eth = Decimal(str(self.w3.from_wei(balance_wei, 'ether')))
        return TokenBalance(
            symbol=self.native_symbol,
            address="native",
            balance=balance_eth,
            decimals=18
        )

    def get_token_price_by_contract(self, token_address: str, chain: str) -> Decimal:
        """Holt ERC-20 Token-Preis via CoinGecko contract lookup."""
        cache_key = f"{chain}:{token_address.lower()}"
        cached = _cached_price(cache_key)
        if cached is not None:
            return cached

        platform = COINGECKO_PLATFORMS.get(chain)
        if not platform:
            return Decimal('0')

        try:
            resp = requests.get(
                f'https://api.coingecko.com/api/v3/simple/token_price/{platform}',
                params={'contract_addresses': token_address.lower(), 'vs_currencies': 'usd'},
                timeout=10
            )
            if resp.ok:
                data = resp.json()
                price = Decimal(str(data.get(token_address.lower(), {}).get('usd', 0)))
                _store_price(cache_key, price)
                return price
        except Exception:
            pass

        _store_price(cache_key, Decimal('0'))
        return Decimal('0')

class EVMChainScanner(BaseChainScanner):
    """Scanner für EVM-basierte Chains (ETH, BSC, Polygon, etc.)"""

    ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"}]'

    KNOWN_TOKENS = {
        'ethereum': {
            'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'DAI':  '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
        },
        'bsc': {
            'USDT': '0x55d398326f99059fF775485246999027B3197955',
            'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
            'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
            'DAI':  '0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3',
        },
        'polygon': {
            'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
            'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
            'DAI':  '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
            'WBTC': '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
        },
        'arbitrum': {
            'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
            'USDC': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
            'DAI':  '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
            'WBTC': '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f',
        },
        'optimism': {
            'USDT': '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58',
            'USDC': '0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
            'DAI':  '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
            'WBTC': '0x68f180fcCe6836688e9084f035309E29Bf0A2095',
        },
        'avalanche': {
            'USDT': '0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7',
            'USDC': '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E',
            'DAI':  '0xd586E7F844cEa2F87f50152665BCbc2C279D8d70',
        },
        'base': {
            'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            'DAI':  '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
        },
    }

    def __init__(self, rpc_url: str, chain_id: int, native_symbol: str, chain_name: str):
        super().__init__(rpc_url, chain_id, native_symbol)
        self.chain_name = chain_name
        self._native_price: Optional[Decimal] = None

    def _get_native_price(self) -> Decimal:
        if self._native_price is None:
            prices = fetch_native_prices([self.chain_name])
            self._native_price = prices.get(self.chain_name, Decimal('0'))
        return self._native_price

    def scan(self, address: str, wallet_name: str, min_value: Decimal) -> WalletScan:
        """Scannt eine EVM-Wallet und berechnet USD-Werte."""
        checksum_addr = self.w3.to_checksum_address(address)

        native_price = self._get_native_price()

        # Native Balance
        native = self.get_native_balance(checksum_addr)
        native.value_usd = (native.balance * native_price).quantize(Decimal('0.01'))

        # Token Balances
        tokens = []
        known = self.KNOWN_TOKENS.get(self.chain_name, {})

        for symbol, token_addr in known.items():
            try:
                balance = self.get_token_balance(checksum_addr, token_addr)
                if balance.balance > 0:
                    price = self.get_token_price_by_contract(token_addr, self.chain_name)
                    balance.value_usd = (balance.balance * price).quantize(Decimal('0.01'))
                    tokens.append(balance)
            except Exception as e:
                print(f"    ⚠️  {symbol}: {str(e)[:60]}")

        total_value = (native.value_usd or Decimal('0')) + sum(
            t.value_usd or Decimal('0') for t in tokens
        )

        return WalletScan(
            wallet_name=wallet_name,
            address=address,
            chain=self.chain_name,
            native_balance=native,
            tokens=tokens,
            total_value_usd=total_value
        )

    def get_token_balance(self, wallet_address: str, token_address: str) -> TokenBalance:
        """Holt ERC-20 Token Balance."""
        contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(token_address),
            abi=self.ERC20_ABI
        )
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        raw = contract.functions.balanceOf(wallet_address).call()
        balance = Decimal(raw) / (Decimal(10) ** decimals)
        return TokenBalance(symbol=symbol, address=token_address, balance=balance, decimals=decimals)

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
