from pymodbus.client import ModbusTcpClient
import time

def test_modbus_client():
    client = ModbusTcpClient('127.0.0.1', port=5020)
    client.connect()
    print("Connected to Modbus Slave")
    
    time.sleep(1)
    
    try:
        print("\n--- Reading Holding Registers ---")
        rr = client.read_holding_registers(address=1, count=8, device_id=1)
        if not rr.isError():
            print(f"Holding registers 1-8: {rr.registers}")
        else:
            print(f"Error reading holding registers: {rr}")
        
        print("\n--- Reading Coils ---")
        rc = client.read_coils(address=1, count=5, device_id=1)
        if not rc.isError():
            print(f"Coils 1-5: {rc.bits}")
        else:
            print(f"Error reading coils: {rc}")
        
        print("\n--- Writing to Holding Register ---")
        ww = client.write_register(address=1, value=9999, device_id=1)
        if not ww.isError():
            print("Write successful!")
        else:
            print(f"Error writing register: {ww}")
        
        time.sleep(1)
        
        print("\n--- Reading Holding Registers after write ---")
        rr = client.read_holding_registers(address=1, count=8, device_id=1)
        if not rr.isError():
            print(f"Holding registers 1-8: {rr.registers}")
        else:
            print(f"Error reading holding registers: {rr}")
        
        print("\n--- Writing to Coil ---")
        wc = client.write_coil(address=1, value=True, device_id=1)
        if not wc.isError():
            print("Coil write successful!")
        else:
            print(f"Error writing coil: {wc}")
        
        time.sleep(1)
        
        print("\n--- Reading Coils after write ---")
        rc = client.read_coils(address=1, count=5, device_id=1)
        if not rc.isError():
            print(f"Coils 1-5: {rc.bits}")
        else:
            print(f"Error reading coils: {rc}")
            
    finally:
        client.close()
        print("\nDisconnected from Modbus Slave")

if __name__ == "__main__":
    test_modbus_client()