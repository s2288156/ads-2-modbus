import time
import pyads

SERVER_AMS_NET_ID = '127.0.0.1.1.1'
SERVER_PORT = 48898
CLIENT_AMS_NET_ID = '127.0.0.1.1.2'

def setup_ads_route():
    try:
        pyads.open_port()
        pyads.set_local_address(CLIENT_AMS_NET_ID)
        pyads.add_route(SERVER_AMS_NET_ID, '127.0.0.1')
    except Exception as e:
        if "already exists" in str(e):
            pass
        else:
            print(f"Route setup warning: {e}")

def test_read_write_bool_variables():
    print("\n=== Testing BOOL variables (Proces.*) ===")

    connection = pyads.Connection(SERVER_AMS_NET_ID, SERVER_PORT)
    connection.open()

    try:
        bool_variables = [
            ('Proces.BoxReady_AM68', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM68_cb', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM71', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM71_cb', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM72', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM72_cb', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM46', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM46_cb', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM56', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM56_cb', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM58', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM58_cb', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM59', pyads.PLCTYPE_BOOL),
            ('Proces.BoxReady_AM59_cb', pyads.PLCTYPE_BOOL),
            ('Proces.PG_Box_Ready_cb', pyads.PLCTYPE_BOOL),
            ('Proces.PG_Full_Ready', pyads.PLCTYPE_BOOL),
            ('Proces.PG_Full_Ready_cb', pyads.PLCTYPE_BOOL),
            ('Proces.PG_Full_End_cb', pyads.PLCTYPE_BOOL),
        ]

        for name, plc_type in bool_variables:
            print(f"\n--- {name} ---")
            try:
                read_value = connection.read_by_name(name, plc_type)
                print(f"  Read: {read_value}")
                
                write_value = not read_value
                connection.write_by_name(name, write_value, plc_type)
                print(f"  Write: {write_value}")
                
                read_value = connection.read_by_name(name, plc_type)
                print(f"  Verify: {read_value}")
                
                if read_value == write_value:
                    print(f"  ✓ PASS")
                else:
                    print(f"  ✗ FAIL: expected {write_value}, got {read_value}")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")

    finally:
        connection.close()

def test_read_write_robot_variables():
    print("\n=== Testing Robot variables (B.* and C.*) ===")

    connection = pyads.Connection(SERVER_AMS_NET_ID, SERVER_PORT)
    connection.open()

    try:
        robot_variables = [
            ('B.robWarningCode_R1', pyads.PLCTYPE_UINT, 1234),
            ('B.batteryLevel_R1', pyads.PLCTYPE_USINT, 85),
            ('C.robWarningCode_R2', pyads.PLCTYPE_UINT, 5678),
            ('C.batteryLevel_R2', pyads.PLCTYPE_USINT, 92),
        ]

        for name, plc_type, write_value in robot_variables:
            print(f"\n--- {name} ---")
            try:
                read_value = connection.read_by_name(name, plc_type)
                print(f"  Read: {read_value}")
                
                connection.write_by_name(name, write_value, plc_type)
                print(f"  Write: {write_value}")
                
                read_value = connection.read_by_name(name, plc_type)
                print(f"  Verify: {read_value}")
                
                if read_value == write_value:
                    print(f"  ✓ PASS")
                else:
                    print(f"  ✗ FAIL: expected {write_value}, got {read_value}")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")

    finally:
        connection.close()

def test_read_write_by_address():
    print("\n=== Testing read/write by address ===")

    connection = pyads.Connection(SERVER_AMS_NET_ID, SERVER_PORT)
    connection.open()

    try:
        address_variables = [
            ('Proces.BoxReady_AM68', 0x4020, 0, pyads.PLCTYPE_BOOL, True),
            ('Proces.BoxReady_AM71', 0x4020, 2, pyads.PLCTYPE_BOOL, True),
            ('Proces.BoxReady_AM46', 0x4020, 6, pyads.PLCTYPE_BOOL, True),
            ('Proces.PG_Full_Ready', 0x4020, 16, pyads.PLCTYPE_BOOL, True),
            ('B.batteryLevel_R1', 0x4020, 200, pyads.PLCTYPE_USINT, 100),
            ('B.robWarningCode_R1', 0x4020, 204, pyads.PLCTYPE_UINT, 2000),
            ('C.batteryLevel_R2', 0x4020, 400, pyads.PLCTYPE_USINT, 100),
            ('C.robWarningCode_R2', 0x4020, 404, pyads.PLCTYPE_UINT, 3000),
        ]

        for name, index_group, index_offset, plc_type, write_value in address_variables:
            print(f"\n--- {name} (0x{index_group:X}:{index_offset}) ---")
            try:
                read_value = connection.read(index_group, index_offset, plc_type)
                print(f"  Read: {read_value}")
                
                connection.write(index_group, index_offset, write_value, plc_type)
                print(f"  Write: {write_value}")
                
                read_value = connection.read(index_group, index_offset, plc_type)
                print(f"  Verify: {read_value}")
                
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
            'Proces.BoxReady_AM68',
            'Proces.BoxReady_AM71',
            'B.robWarningCode_R1',
            'B.batteryLevel_R1',
            'C.robWarningCode_R2',
            'C.batteryLevel_R2',
        ]
        
        print("\n--- read_list_by_name ---")
        values = connection.read_list_by_name(names)
        for name, value in zip(names, values):
            print(f"  {name}: {value}")

        print("\n--- write_list_by_name ---")
        values_to_write = {
            'Proces.BoxReady_AM68': True,
            'Proces.BoxReady_AM71': True,
            'B.robWarningCode_R1': 100,
            'B.batteryLevel_R1': 50,
            'C.robWarningCode_R2': 200,
            'C.batteryLevel_R2': 75,
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

    test_read_write_bool_variables()
    test_read_write_robot_variables()
    test_read_write_by_address()
    test_list_operations()

    print("\n=== All tests completed ===")