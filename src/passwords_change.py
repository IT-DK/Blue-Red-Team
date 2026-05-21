import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

from pwn import ssh


def change_password_for_host(ip: str, password: str, old_password: str = "changeme", timeout: int = 10) -> Tuple[str, bool, str]:
    """Zmienia hasło na pojedynczym hoście.
    
    Args:
        ip: Adres IP hosta
        password: Nowe hasło do ustawienia
        old_password: Stare hasło (domyślnie '***')
        timeout: Timeout połączenia SSH w sekundach
    
    Returns:
        tuple: (ip, success, message)
    """
    try:
        print(f"Próba logowania do {ip}...")
        # Logowanie na domyślne dane
        s = ssh(user='root', host=ip, password=old_password, timeout=timeout)
        
        # Zmiana hasła użytkownika root przy użyciu chpasswd
        s.run(f"echo 'root:{password}' | sudo chpasswd")
        
        s.close()
        message = f"Hasło na {ip} zostało pomyślnie zmienione."
        print(message)
        return (ip, True, message)
    except Exception as e:
        message = f"Nie udało się połączyć z {ip}: {e}"
        print(message)
        return (ip, False, message)


async def change_passwords_async(hosts: List[str], password: str, old_password: str = "***") -> List[Tuple[str, bool, str]]:
    """Zmienia hasła na wszystkich hostach asynchronicznie.
    
    Args:
        hosts: Lista adresów IP hostów
        password: Nowe hasło do ustawienia
        old_password: Stare hasło (domyślnie '***')
    
    Returns:
        Lista wyników dla każdego hosta: [(ip, success, message), ...]
    """
    # Handle empty host list
    if not hosts:
        print("Brak hostów do przetworzenia.")
        return []
    
    loop = asyncio.get_event_loop()
    
    # Używamy ThreadPoolExecutor do wykonywania operacji SSH równolegle
    with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        tasks = [
            loop.run_in_executor(executor, change_password_for_host, ip, password, old_password)
            for ip in hosts
        ]
        
        # Czekamy na zakończenie wszystkich zadań
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Podsumowanie
    print("\n" + "="*60)
    print("PODSUMOWANIE:")
    print("="*60)
    
    successful = [r for r in results if isinstance(r, tuple) and r[1]]
    failed = [r for r in results if isinstance(r, tuple) and not r[1]]
    errors = [r for r in results if not isinstance(r, tuple)]
    
    print(f"Udane: {len(successful)}/{len(hosts)}")
    print(f"Nieudane: {len(failed)}/{len(hosts)}")
    if errors:
        print(f"Błędy: {len(errors)}")
    
    if failed:
        print("\nNieudane hosty:")
        for ip, _, msg in failed:
            print(f"  - {ip}")
    
    return results
