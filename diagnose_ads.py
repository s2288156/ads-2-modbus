#!/usr/bin/env python3
"""Deep ADS diagnostics - try every combination of port/read-method.

Usage:
  python3 diagnose_ads.py
  python3 diagnose_ads.py --plc-user Administrator --plc-pass 1
"""
import argparse
import socket

import pyads

PLC_AMS_NET_ID = "192.168.199.80.1.1"
PLC_IP = "172.168.1.201"
TIMEOUT = 5000


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((PLC_IP, 80))
        return s.getsockname()[0]
    finally:
        s.close()


def run(local_ams, plc_user, plc_pass):
    local_ip = get_local_ip()
    if not local_ams:
        local_ams = f"{local_ip}.1.1"

    print(f"=== ADS Deep Diagnostics ===")
    print(f"PLC:      {PLC_AMS_NET_ID} @ {PLC_IP}")
    print(f"Local:    {local_ams} @ {local_ip}")
    print()

    # Setup
    pyads.open_port()
    pyads.set_local_address(local_ams)
    try:
        pyads.add_route(PLC_AMS_NET_ID, PLC_IP)
    except Exception:
        pass

    if plc_user and plc_pass:
        print("[*] Adding PLC-side route...")
        try:
            pyads.add_route_to_plc(local_ams, PLC_IP, PLC_IP,
                                   plc_user, plc_pass,
                                   route_name="DiagTest")
            print(f"    OK")
        except Exception as e:
            print(f"    {e}")

    # Scan ports - 851 first (PLC Runtime 1), then others
    ports = [851, 852, 853, 854, 855, 48898]

    print(f"\n[*] Scanning {len(ports)} ports...")
    for port in ports:
        print(f"\n--- Port {port} ---")
        conn = pyads.Connection(PLC_AMS_NET_ID, port, ip_address=PLC_IP)
        conn.set_timeout(TIMEOUT)
        try:
            conn.open()
            print(f"  Connection: OK")
        except Exception as e:
            print(f"  Connection: FAIL ({e})")
            conn.close()
            continue

        # Test 1: read_device_info
        try:
            info = conn.read_device_info()
            print(f"  read_device_info: OK (device={info.device_name})")
        except Exception as e:
            print(f"  read_device_info: FAIL ({e})")

        # Test 2: read(0x4020, 0)
        try:
            val = conn.read(0x4020, 0, pyads.PLCTYPE_BOOL)
            print(f"  read(0x4020,0):   OK (value={val})")
        except Exception as e:
            print(f"  read(0x4020,0):   FAIL ({e})")

        # Test 3: read_by_name
        try:
            val = conn.read_by_name('Proces.BoxReady_AM68', pyads.PLCTYPE_BOOL)
            print(f"  read_by_name:     OK (value={val})")
        except Exception as e:
            print(f"  read_by_name:     FAIL ({e})")

        # Test 4: get_symbol
        try:
            sym = conn.get_symbol('Proces.BoxReady_AM68')
            print(f"  get_symbol:       OK (ig=0x{sym.index_group:X} "
                  f"io={sym.index_offset} type={sym.plc_type})")
            val = sym.read()
            print(f"  sym.read():       OK (value={val})")
        except Exception as e:
            print(f"  get_symbol:       FAIL ({e})")

        # Test 5: read using symbol's own index_group/offset (if obtained)
        try:
            sym = conn.get_symbol('Proces.BoxReady_AM68')
            val = conn.read(sym.index_group, sym.index_offset, sym.plc_type)
            print(f"  read(ig,io,type): OK (value={val})")
        except Exception:
            pass

        # Test 6: IO image read
        try:
            val = conn.read(0xF020, 0, pyads.PLCTYPE_BOOL)
            print(f"  IO image read:    OK (value={val})")
        except Exception as e:
            print(f"  IO image read:    FAIL ({e})")

        conn.close()

    print(f"\n=== Done ===")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-ams', default=None)
    parser.add_argument('--plc-user', default=None)
    parser.add_argument('--plc-pass', default=None)
    args = parser.parse_args()
    run(args.local_ams, args.plc_user, args.plc_pass)
