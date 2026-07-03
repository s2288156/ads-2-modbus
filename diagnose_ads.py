#!/usr/bin/env python3
"""Diagnose ADS read issues: test different read methods to find the root cause.

Usage: python3 diagnose_ads.py --net-id <PLC_AMS_NET_ID> --route-ip <PLC_IP>
"""
import argparse
import pyads


def diagnose(ams_net_id, port, route_ip, timeout):
    print(f"=== ADS Diagnostics ===")
    print(f"AMS Net ID: {ams_net_id}")
    print(f"Port:       {port}")
    print(f"Route IP:   {route_ip}")
    print(f"Timeout:    {timeout}ms")
    print()

    # 1. Add route
    print("[1] Adding ADS route...")
    try:
        pyads.open_port()
        if route_ip:
            pyads.add_route(ams_net_id, route_ip)
            print(f"    Route added: {ams_net_id} -> {route_ip}")
    except Exception as e:
        if "already exists" in str(e):
            print(f"    Route already exists")
        else:
            print(f"    Route failed: {e}")

    # 2. Open connection
    print("\n[2] Opening ADS connection...")
    conn = pyads.Connection(ams_net_id, port, ip_address=route_ip if route_ip else None)
    try:
        conn.open()
        conn.set_timeout(timeout)
        print(f"    Connected OK")
    except Exception as e:
        print(f"    Connection failed: {e}")
        return

    try:
        # 3. Test read_device_info (uses 0xF100)
        print("\n[3] Test read_device_info (0xF100, should pass)...")
        try:
            info = conn.read_device_info()
            print(f"    PASS: device={info.device_name}, version={info.version}")
        except Exception as e:
            print(f"    FAIL: {e}")

        # 4. Test read(0x4020, 0) - bool
        print("\n[4] Test read(0x4020, 0, PLCTYPE_BOOL)...")
        try:
            val = conn.read(0x4020, 0, pyads.PLCTYPE_BOOL)
            print(f"    PASS: value={val}")
        except Exception as e:
            print(f"    FAIL: {e}")

        # 5. Test read_by_name
        print("\n[5] Test read_by_name('Proces.BoxReady_AM68', PLCTYPE_BOOL)...")
        try:
            val = conn.read_by_name('Proces.BoxReady_AM68', pyads.PLCTYPE_BOOL)
            print(f"    PASS: value={val}")
        except Exception as e:
            print(f"    FAIL: {e}")

        # 6. Test get_symbol + handle read
        print("\n[6] Test get_symbol + handle read...")
        try:
            sym = conn.get_symbol('Proces.BoxReady_AM68')
            print(f"    symbol: name={sym.name}, index_group=0x{sym.index_group:X}, index_offset={sym.index_offset}, type={sym.plc_type}")
            val = sym.read()
            print(f"    PASS: value={val}")
        except Exception as e:
            print(f"    FAIL: {e}")

        # 7. Read using symbol's index_group/index_offset
        print("\n[7] Read using symbol's index_group/index_offset...")
        try:
            sym = conn.get_symbol('Proces.BoxReady_AM68')
            val = conn.read(sym.index_group, sym.index_offset, sym.plc_type)
            print(f"    PASS: value={val}")
            print(f"    index_group=0x{sym.index_group:X}, index_offset={sym.index_offset}")
        except Exception as e:
            print(f"    FAIL: {e}")

        # 8. Try different timeout values
        print("\n[8] Test different timeout values on 0x4020:0x0...")
        for t in [5000, 10000, 20000]:
            conn.set_timeout(t)
            try:
                val = conn.read(0x4020, 0, pyads.PLCTYPE_BOOL)
                print(f"    timeout={t}ms -> PASS: value={val}")
                break
            except Exception as e:
                print(f"    timeout={t}ms -> FAIL: {e}")

    finally:
        conn.close()
        print("\nConnection closed")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ADS Diagnostics Tool')
    parser.add_argument('--net-id', required=True, help='PLC AMS Net ID')
    parser.add_argument('--port', type=int, default=48898, help='ADS port (default: 48898)')
    parser.add_argument('--route-ip', default='', help='PLC IP address')
    parser.add_argument('--timeout', type=int, default=5000, help='Timeout in ms (default: 5000)')
    args = parser.parse_args()
    diagnose(args.net_id, args.port, args.route_ip, args.timeout)
