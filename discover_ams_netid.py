#!/usr/bin/env python3
"""Discover the AMS Net ID of a TwinCAT PLC by IP address.

Tries multiple methods to find the correct AMS Net ID for a given PLC IP.
"""
import argparse
import sys

import pyads


def discover(ip, port, local_ams=None):
    print(f"=== AMS Net ID Discovery ===")
    print(f"Target IP:  {ip}")
    print(f"ADS Port:   {port}")
    print()

    # Method 1: pyads built-in resolver
    print("[1] pyads.adsGetNetIdForPLC...")
    try:
        pyads.open_port()
        netid = pyads.adsGetNetIdForPLC(ip)
        print(f"    Found: {netid}")
        return netid
    except Exception as e:
        print(f"    Failed: {e}")

    # Method 2: try common Net ID patterns based on IP
    print(f"\n[2] Trying common Net ID patterns for {ip}...")
    octets = ip.split('.')
    if len(octets) == 4:
        candidates = [
            f"{ip}.1.1",
            f"{ip}.1.2",
            f"{ip}.2.1",
            f"{ip}.3.1",
        ]

        for netid in candidates:
            try:
                if local_ams:
                    pyads.set_local_address(local_ams)
                pyads.add_route(netid, ip)
                conn = pyads.Connection(netid, port, ip_address=ip)
                conn.open()
                info = conn.read_device_info()
                conn.close()
                print(f"    Found: {netid} (device={info.device_name})")
                return netid
            except pyads.ADSError as e:
                err = getattr(e, 'err_code', None)
                if err == 6:
                    print(f"    {netid} -> ADS server not started on this port")
                elif err == 7:
                    print(f"    {netid} -> timeout (wrong Net ID or unreachable)")
                else:
                    print(f"    {netid} -> error {err}: {e}")
            except Exception as e:
                print(f"    {netid} -> {e}")

    # Method 3: scan different ADS ports
    print(f"\n[3] Scanning common ADS ports on {ip}...")
    common_ports = [851, 852, 853, 48898]
    netid = f"{ip}.1.1"

    for p in common_ports:
        try:
            pyads.add_route(netid, ip)
            conn = pyads.Connection(netid, p, ip_address=ip)
            conn.open()
            info = conn.read_device_info()
            conn.close()
            print(f"    Port {p}: FOUND! device={info.device_name}, version={info.version}")
            print(f"    Net ID: {netid}, Port: {p}")
            return netid, p
        except pyads.ADSError as e:
            err = getattr(e, 'err_code', None)
            print(f"    Port {p}: error {err}")
        except Exception as e:
            print(f"    Port {p}: {e}")

    print("\n[!] Could not discover AMS Net ID. Please check:")
    print("    - Is the PLC powered on and in RUN mode?")
    print("    - Is TwinCAT ADS Router running on the PLC?")
    print("    - Is the IP address correct and reachable? (ping it)")
    print("    - Are there firewall rules blocking ADS traffic?")
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Discover AMS Net ID for a TwinCAT PLC')
    parser.add_argument('--ip', required=True, help='PLC IP address')
    parser.add_argument('--port', type=int, default=48898, help='ADS port (default: 48898)')
    parser.add_argument('--local-ams', default=None, help='Local AMS Net ID (optional)')
    args = parser.parse_args()
    discover(args.ip, args.port, args.local_ams)
