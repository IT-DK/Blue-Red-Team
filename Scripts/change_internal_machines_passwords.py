import sys
sys.path.insert(0, '..')

import asyncio
from src.vm_ip_map_utils import get_our_internal_ips
from src.passwords_change import change_passwords_async


def main():
    """Główna funkcja zmieniająca hasła na wszystkich naszych maszynach."""
    # Adresy IP naszych usług w sieci wewnętrznej - pobierane automatycznie na podstawie dnia
    targets = get_our_internal_ips()  # Używa config.DAY z pliku konfiguracyjnego
    new_password = "TwojeNoweBezpieczneHaslo"
    
    print(f"Rozpoczynam zmianę haseł dla {len(targets)} hostów...")
    print(f"Hosty: {', '.join(targets)}\n")
    
    # Uruchamiamy asynchroniczną zmianę haseł
    asyncio.run(change_passwords_async(targets, new_password))


if __name__ == "__main__":
    main()
