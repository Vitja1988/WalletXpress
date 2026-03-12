#!/usr/bin/env python3
"""
WalletXpress - Multi-Chain Wallet Consolidation Tool
Haupt-Einstiegspunkt
"""

import argparse
import sys
from colorama import init, Fore, Style

init()  # Colorama initialisieren

def print_banner():
    print(Fore.CYAN + """
╦ ╦┌─┐┬  ┬┌─┐┌─┐┌┐┌┌─┐┌─┐
║║║├┤ └┐┌┘├┤ │ ││││├┤ └─┐
╚╩╝└─┘ └┘ └─┘└─┘┘└┘└─┘└─┘
Multi-Chain Wallet Consolidator
""" + Style.RESET_ALL)

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='Automatisiere Transfers zwischen deinen Wallets'
    )
    
    parser.add_argument(
        '--scan', 
        action='store_true',
        help='Scanne alle Wallets und zeige Balances'
    )
    
    parser.add_argument(
        '--plan',
        action='store_true', 
        help='Erstelle Transfer-Plan (zeigt was transferiert würde)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simuliere Transfers ohne echtes Senden'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Führe echte Transfers durch (ACHTUNG!)'
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Pfad zur Config-Datei'
    )
    
    args = parser.parse_args()
    
    # Mindestens ein Befehl muss angegeben sein
    if not any([args.scan, args.plan, args.dry_run, args.execute]):
        parser.print_help()
        sys.exit(1)
    
    # --- SCAN ---
    if args.scan:
        print(Fore.YELLOW + "\n🔍 Starte Wallet-Scan..." + Style.RESET_ALL)
        from src.scanner import WalletScanner
        
        scanner = WalletScanner(args.config)
        scans = scanner.scan_all_wallets()
        scanner.print_scan_summary(scans)
    
    # --- PLAN ---
    elif args.plan:
        print(Fore.YELLOW + "\n📋 Erstelle Transfer-Plan..." + Style.RESET_ALL)
        from src.scanner import WalletScanner
        
        scanner = WalletScanner(args.config)
        scans = scanner.scan_all_wallets()
        plan = scanner.calculate_transfer_plan(scans)
        
        print(f"\n{Fore.GREEN}TRANSFER-PLAN:{Style.RESET_ALL}")
        print(f"Wallets: {plan['total_wallets']}")
        print(f"Chains: {plan['total_chains']}")
        print(f"Geplante Transfers: {plan['total_transfers']}")
        print(f"Gesamtwert: ${plan['total_value_usd']:.2f}")
        
        print(f"\n{Fore.CYAN}Transfers:{Style.RESET_ALL}")
        for tx in plan['transfers'][:10]:  # Zeige max 10
            print(f"  {tx['token']} ({tx['chain']}): {float(tx['amount']):.4f} → ${tx['value_usd']:.2f}")
        if len(plan['transfers']) > 10:
            print(f"  ... und {len(plan['transfers']) - 10} weitere")
    
    # --- DRY-RUN oder EXECUTE ---
    elif args.dry_run or args.execute:
        if args.execute:
            print(Fore.RED + "\n⚠️  WARNUNG: ECHTE TRANSFERS!" + Style.RESET_ALL)
            confirm = input("Bist du sicher? (ja/Nein): ")
            if confirm.lower() != "ja":
                print("Abgebrochen.")
                sys.exit(0)
        else:
            print(Fore.YELLOW + "\n⏸️  DRY-RUN MODE (Simulation)" + Style.RESET_ALL)
        
        # Scanner laufen lassen
        from src.scanner import WalletScanner
        scanner = WalletScanner(args.config)
        scans = scanner.scan_all_wallets()
        plan = scanner.calculate_transfer_plan(scans)
        
        # Transfers ausführen
        from src.transfer import TransferExecutor, Transfer
        from decimal import Decimal
        
        # Konvertiere Plan zu Transfer-Objekten
        transfers = []
        for tx_data in plan['transfers']:
            transfers.append(Transfer(
                from_wallet=tx_data['from'],
                to_wallet=tx_data['to'],
                chain=tx_data['chain'],
                token=tx_data['token'],
                token_address=tx_data.get('token_address', 'native'),
                amount=Decimal(str(tx_data['amount'])),
                value_usd=Decimal(str(tx_data['value_usd']))
            ))
        
        executor = TransferExecutor(args.config)
        results = executor.execute_transfers(transfers)
        
        # Zusammenfassung
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')
        
        print(f"\n{Fore.GREEN}✅ Erfolgreich: {successful}{Style.RESET_ALL}")
        if failed:
            print(f"{Fore.RED}❌ Fehlgeschlagen: {failed}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
