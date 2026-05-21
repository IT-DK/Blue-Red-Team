#!/usr/bin/env python3

import os
import paramiko
from scp import SCPClient
from datetime import datetime

# ============================================
# Skrypt do backupu folderów z /opt/ z wielu VMS
# ============================================

# ----- KONFIGURACJA -----

# Definicja VMS
VMS = [
    {"id": "server1",       "name": "server1",       "ip": "172.28.0.101"},
    {"id": "server2",        "name": "server2",        "ip": "172.28.0.102"},
    {"id": "server3",       "name": "server3",       "ip": "172.28.0.103"},
    {"id": "server4", "name": "server4",  "ip": "172.28.0.105"},
    {"id": "server5",     "name": "server5",      "ip": "172.28.0.106"},
    {"id": "server6",    "name": "server6",     "ip": "172.28.0.109"},
    {"id": "server7",    "name": "server7",      "ip": "172.28.0.110"},
    {"id": "server8",   "name": "server8",     "ip": "172.28.0.112"},
]

# Lista VM ID do backupu (automatycznie użyje folderu {id}-app)
BACKUP_VMS = [
    "server1",
    "server2",
    "server3",
    "server4",
    "server5",
    "server6",
    "server7",
    "server8",
]

# Użytkownik SSH
USER = "debian"

# Hasło SSH
PASSWORD = "***"

# GŁÓWNY FOLDER DO BACKUPÓW - ZDEFINIUJ TUTAJ SWOJĄ ŚCIEŻKĘ
BACKUP_ROOT = "/home/***/Backups"  # <--- ZMIEŃ TO NA SWOJĄ ŚCIEŻKĘ

# Rotacja backupów - zachowaj tylko 2 ostatnie backupy
KEEP_LAST_BACKUPS = 2

# ----- KONIEC KONFIGURACJI -----

# Pomocniczy słownik dla szybkiego dostępu do VM po ID
VMS_DICT = {vm["id"]: vm for vm in VMS}

def create_ssh_client(server, username, password):
    """Tworzy połączenie SSH z serwerem"""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(server, username=username, password=password, timeout=30)
        return client
    except Exception as e:
        print(f"✗ Błąd połączenia z {server}: {e}")
        return None

def download_folder(vm_info, username, password, backup_dir):
    """Pobiera folder {id}-app ze zdalnego serwera"""
    server = vm_info["ip"]
    vm_name = vm_info["name"]
    vm_id = vm_info["id"]
    
    # Format folderu: {id}-app
    folder_name = f"{vm_id}-app"
    remote_path = f"/opt/{folder_name}"
    
    print(f"\nPobieranie: {vm_name} ({server}) -> /opt/{folder_name}")
    print("-" * 70)
    
    # Utworzenie struktury folderów: backup_dir/vm_id/
    server_backup_dir = os.path.join(backup_dir, vm_id)
    os.makedirs(server_backup_dir, exist_ok=True)
    
    # Połączenie SSH
    ssh = create_ssh_client(server, username, password)
    if ssh is None:
        return False
    
    try:
        # Sprawdź czy folder istnieje na zdalnym serwerze
        stdin, stdout, stderr = ssh.exec_command(f'test -d {remote_path} && echo "exists"')
        if stdout.read().decode().strip() != "exists":
            print(f"⚠ Folder {remote_path} nie istnieje na serwerze {vm_name} ({server})")
            ssh.close()
            return False
        
        # Utworzenie klienta SCP
        with SCPClient(ssh.get_transport()) as scp:
            # Pobierz folder
            scp.get(remote_path, server_backup_dir, recursive=True)
        
        print(f"✓ Pobrano pomyślnie: {vm_name}/opt/{folder_name}")
        return True
        
    except Exception as e:
        print(f"✗ Błąd podczas pobierania z {vm_name}/opt/{folder_name}: {e}")
        return False
        
    finally:
        ssh.close()

def cleanup_old_backups(backup_root, keep_last):
    """Usuwa stare backupy, zachowując tylko określoną liczbę ostatnich"""
    if keep_last <= 0:
        return
    
    try:
        # Pobierz listę folderów backupów
        backup_dirs = []
        for item in os.listdir(backup_root):
            full_path = os.path.join(backup_root, item)
            if os.path.isdir(full_path) and item.startswith("backup_"):
                backup_dirs.append((full_path, os.path.getctime(full_path)))
        
        # Sortuj po dacie utworzenia (najstarsze pierwsze)
        backup_dirs.sort(key=lambda x: x[1])
        
        # Usuń stare backupy (zostaw tylko keep_last najnowszych)
        to_delete = len(backup_dirs) - keep_last
        if to_delete > 0:
            print(f"\n{'=' * 70}")
            print(f"ROTACJA BACKUPÓW - Usuwanie {to_delete} starych backupów...")
            print(f"Zachowuję {keep_last} najnowsze backupy")
            print(f"{'=' * 70}")
            for i in range(to_delete):
                dir_path = backup_dirs[i][0]
                dir_name = os.path.basename(dir_path)
                print(f"  🗑 Usuwanie: {dir_name}")
                os.system(f'rm -rf "{dir_path}"')
            print(f"✓ Rotacja zakończona")
        else:
            print(f"\n✓ Brak starych backupów do usunięcia (jest {len(backup_dirs)}/{keep_last})")
    
    except Exception as e:
        print(f"✗ Błąd podczas czyszczenia starych backupów: {e}")

def main():
    """Główna funkcja skryptu"""
    # Utworzenie timestampa dla tego backupu
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # Folder dla tego konkretnego backupu
    current_backup_dir = os.path.join(BACKUP_ROOT, f"backup_{timestamp}")
    
    print("=" * 70)
    print("BACKUP FOLDERÓW {ID}-APP Z /opt/ Z VMS")
    print(f"Timestamp: {timestamp}")
    print(f"Liczba VMS: {len(BACKUP_VMS)}")
    print(f"Lokalizacja backupu: {current_backup_dir}")
    print(f"Rotacja: Zachowuję {KEEP_LAST_BACKUPS} najnowsze backupy")
    print("=" * 70)
    
    # Wyświetl plan backupu
    print("\nPlan backupu:")
    for vm_id in BACKUP_VMS:
        if vm_id in VMS_DICT:
            vm_name = VMS_DICT[vm_id]["name"]
            vm_ip = VMS_DICT[vm_id]["ip"]
            folder = f"{vm_id}-app"
            print(f"  {vm_name} ({vm_ip}): /opt/{folder}")
        else:
            print(f"  ⚠ Nieznany VM ID: {vm_id}")
    
    # Utworzenie folderu na backupy
    os.makedirs(current_backup_dir, exist_ok=True)
    
    # Statystyki
    success_count = 0
    fail_count = 0
    
    # Pobieranie z każdego serwera
    for vm_id in BACKUP_VMS:
        if vm_id not in VMS_DICT:
            print(f"\n✗ Nieznany VM ID: {vm_id}")
            fail_count += 1
            continue
        
        vm_info = VMS_DICT[vm_id]
        if download_folder(vm_info, USER, PASSWORD, current_backup_dir):
            success_count += 1
        else:
            fail_count += 1
    
    # Czyszczenie starych backupów
    cleanup_old_backups(BACKUP_ROOT, KEEP_LAST_BACKUPS)
    
    # Podsumowanie
    print("\n" + "=" * 70)
    print("BACKUP ZAKOŃCZONY")
    print(f"Sukces: {success_count}/{len(BACKUP_VMS)} | Błędy: {fail_count}")
    print(f"Lokalizacja: {current_backup_dir}")
    print(f"Czas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

if __name__ == "__main__":
    main()
