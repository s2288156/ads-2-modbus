#!/usr/bin/env python3
"""Discover AMS Net ID and diagnose ADS connectivity to a TwinCAT PLC.

Usage: python3 discover_ams_netid.py --ip <PLC_IP> [--local-ams <LOCAL_AMS>]
"""
import argparse
import socket
import subprocess
import sys

import pyads


def check_network(ip):
    """Basic network connectivity checks before trying ADS."""
    print(f"=== Step 1: Network Connectivity ===")

    # ping
    print(f"\n[ping] {ip}...")
    try:
        result = subprocess.run(
            ['ping', '-c', '3', '-W', '2', ip],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # extract avg latency
            for line in result.stdout.splitlines():
                if 'avg' in line or 'round-trip' in line:
                    print(f"    OK: {line.strip()}")
                    break
            else:
                print(f"    OK: reachable")
        else:
            print(f"    FAIL: not reachable")
            print(f"    {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"    FAIL: {e}")
        return False

    # TCP port scan
    print(f"\n[tcp] Scanning common ADS ports on {ip}...")
    ads_ports = [48898, 851, 852, 853]
    any_open = False
    for p in ads_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, p))
        sock.close()
        if result == 0:
            print(f"    Port {p}: OPEN")
            any_open = True
        else:
            print(f"    Port {p}: closed/unreachable")
    return any_open


def discover_by_name(ip, port, local_ams):
    """Use TC1/TwinCAT Engineering route name to discover Net ID."""
    print(f"\n=== Step 2: Discover via ADS ===")

    if local_ams:
        print(f"\n[local] Setting local AMS Net ID: {local_ams}")
        pyads.open_port()
        pyads.set_local_address(local_ams)

    # Try common Net ID patterns
    print(f"\n[pattern] Trying common Net ID patterns...")
    candidates = [
        f"{ip}.1.1",
        f"{ip}.1.2",
        f"{ip}.2.1",
        f"{ip}.3.1",
    ]

    for netid in candidates:
        try:
            pyads.add_route(netid, ip)
            conn = pyads.Connection(netid, port, ip_address=ip)
            conn.set_timeout(3000)
            conn.open()
            info = conn.read_device_info()
            conn.close()
            print(f"    FOUND: Net ID = {netid}")
            print(f"    Device: {info.device_name}")
            print(f"    Version: {info.version}")
            return netid
        except pyads.ADSError as e:
            err = getattr(e, 'err_code', None)
            print(f"    {netid} -> error {err}")
        except Exception as e:
            print(f"    {netid} -> {e}")

    # Try reading from existing config if available
    print(f"\n[config] Trying to read config for existing AMS Net ID...")
    try:
        import yaml
        with open('config/mapping.yaml') as f:
            config = yaml.safe_load(f)
        existing_netid = config.get('ads_connection', {}).get('ams_net_id', '')
        if existing_netid and existing_netid != ip:
            print(f"    Found in config: {existing_netid}")
            try:
                pyads.add_route(existing_netid, ip)
                conn = pyads.Connection(existing_netid, port, ip_address=ip)
                conn.set_timeout(3000)
                conn.open()
                info = conn.read_device_info()
                conn.close()
                print(f"    WORKS! Net ID = {existing_netid}")
                print(f"    Device: {info.device_name}")
                return existing_netid
            except pyads.ADSError as e:
                err = getattr(e, 'err_code', None)
                print(f"    Failed: error {err}")
    except Exception:
        print(f"    No config found or parse error")

    return None


def main():
    parser = argparse.ArgumentParser(description='Discover AMS Net ID for TwinCAT PLC')
    parser.add_argument('--ip', required=True, help='PLC IP address')
    parser.add_argument('--port', type=int, default=48898, help='ADS port (default: 48898)')
    parser.add_argument('--local-ams', default=None, help='Local AMS Net ID')
    args = parser.parse_args()

    print(f"=== AMS Net ID Discovery ===")
    print(f"Target IP:  {args.ip}")
    print(f"ADS Port:   {args.port}")
    print()

    # Step 1: network check
    if not check_network(args.ip):
        print(f"\n[!] Network to {args.ip} is not reachable. Fix network first.")
        sys.exit(1)

    # Step 2: ADS discovery
    netid = discover_by_name(args.ip, args.port, args.local_ams)

    if netid:
        print(f"\n=== RESULT ===")
        print(f"Use this in config/mapping.yaml:")
        print(f"  ams_net_id: \"{netid}\"")
        print(f"  route_ip:   \"{args.ip}\"")
        print(f"  port:       {args.port}")
    else:
        print(f"\n[!] Could not discover Net ID.")
        print(f"    The IP is reachable but ADS communication failed.")
        print(f"    Please check on the PLC side:")
        print(f"    - TwinCAT runtime is in RUN mode")
        print(f"    - ADS service is started (TwinCAT System Manager)")
        print(f"    - No firewall blocking ADS ports (48898/851-853)")


if __name__ == '__main__':
    main()
