import time
import pyads

SERVER_AMS_NET_ID = '127.0.0.1.1.1'
SERVER_PORT = 48888
CLIENT_AMS_NET_ID = '127.0.0.1.1.2'

def setup_ads_route():
    pyads.open_port()
    pyads.set_local_address(CLIENT_AMS_NET_ID)
    try:
        pyads.add_route(SERVER_AMS_NET_ID, '127.0.0.1')
    except Exception as e:
        if "already exists" in str(e):
            pass
        else:
            raise

def test_read_write_by_name():
    print("\n=== Testing read/write by name ===")

    connection = pyads.Connection(SERVER_AMS_NET_ID, SERVER_PORT)
    connection.open()

    try:
        variables = [
            ('GVL.bool_value', True, pyads.PLCTYPE_BOOL),
            ('GVL.int_value', 5678, pyads.PLCTYPE_DINT),
            ('GVL.int16_value', 1234, pyads.PLCTYPE_INT),
            ('GVL.float_value', 6.28, pyads.PLCTYPE_REAL),
            ('GVL.uint16_value', 1000, pyads.PLCTYPE_UINT),
            ('GVL.usint_value', 127, pyads.PLCTYPE_USINT),
            ('GVL.uint32_value', 1234567890, pyads.PLCTYPE_UDINT),
        ]

        for name, write_value, plc_type in variables:
            print(f"\n--- {name} ---")
            try:
                read_value = connection.read_by_name(name, plc_type)
                print(f"  Read: {read_value}")
                
                connection.write_by_name(name, write_value, plc_type)
                print(f"  Write: {write_value}")
                
                read_value = connection.read_by_name(name, plc_type)
                print(f"  Verify: {read_value}")
                
                if isinstance(write_value, float):
                    if abs(read_value - write_value) < 0.001:
                        print(f"  ✓ PASS")
                    else:
                        print(f"  ✗ FAIL: expected {write_value}, got {read_value}")
                else:
                    if read_value == write_value:
                        print(f"  ✓ PASS")
                    else:
                        print(f"  ✗ FAIL: expected {write_value}, got {read_value}")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")

    finally:
        connection.close()

def test_read_write_by_address():
    print("\n=== Testing read/write by address (index_group/index_offset) ===")

    connection = pyads.Connection(SERVER_AMS_NET_ID, SERVER_PORT)
    connection.open()

    try:
        variables = [
            (0x4020, 0, pyads.PLCTYPE_BOOL, False),
            (0x4020, 16, pyads.PLCTYPE_DINT, 9999),
            (0x4020, 20, pyads.PLCTYPE_INT, 8888),
            (0x4020, 32, pyads.PLCTYPE_REAL, 9.99),
            (0x4020, 36, pyads.PLCTYPE_UINT, 5000),
            (0x4020, 38, pyads.PLCTYPE_USINT, 200),
            (0x4020, 40, pyads.PLCTYPE_UDINT, 1000000),
        ]

        for index_group, index_offset, plc_type, write_value in variables:
            print(f"\n--- index_group=0x{index_group:X}, index_offset={index_offset} ---")
            try:
                read_value = connection.read(index_group, index_offset, plc_type)
                print(f"  Read: {read_value}")
                
                connection.write(index_group, index_offset, write_value, plc_type)
                print(f"  Write: {write_value}")
                
                read_value = connection.read(index_group, index_offset, plc_type)
                print(f"  Verify: {read_value}")
                
                if isinstance(write_value, float):
                    if abs(read_value - write_value) < 0.001:
                        print(f"  ✓ PASS")
                    else:
                        print(f"  ✗ FAIL: expected {write_value}, got {read_value}")
                else:
                    if read_value == write_value:
                        print(f"  ✓ PASS")
                    else:
                        print(f"  ✗ FAIL: expected {write_value}, got {read_value}")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")

    finally:
        connection.close()

def test_list_operations():
    print("\n=== Testing list operations ===")

    connection = pyads.Connection(SERVER_AMS_NET_ID, SERVER_PORT)
    connection.open()

    try:
        names = [
            'GVL.bool_value',
            'GVL.int_value',
            'GVL.float_value',
            'GVL.uint16_value',
        ]
        
        print("\n--- read_list_by_name ---")
        values = connection.read_list_by_name(names)
        for name, value in zip(names, values):
            print(f"  {name}: {value}")

        print("\n--- write_list_by_name ---")
        values_to_write = {
            'GVL.bool_value': False,
            'GVL.int_value': 7777,
            'GVL.float_value': 2.71,
            'GVL.uint16_value': 2000,
        }
        connection.write_list_by_name(values_to_write)
        print(f"  Written values: {values_to_write}")

        print("\n--- Verify ---")
        values = connection.read_list_by_name(names)
        for name, value in zip(names, values):
            print(f"  {name}: {value}")

    finally:
        connection.close()

if __name__ == "__main__":
    print("Setting up ADS route...")
    setup_ads_route()
    
    print("\nWaiting for ADS server...")
    time.sleep(1)

    test_read_write_by_name()
    test_read_write_by_address()
    test_list_operations()

    print("\n=== All tests completed ===")
