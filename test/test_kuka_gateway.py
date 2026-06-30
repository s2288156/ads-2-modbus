import asyncio
import logging
import time
import yaml

from pymodbus.client import ModbusTcpClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import from parent package
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import start_kuka_ads_server, load_config
from src.ads_client import ADSClient
from src.modbus_slave import ModbusSlave
from src.data_mapper import DataMapper


def test_modbus_operations(modbus_host, modbus_port, slave_id):
    """Run Modbus client read/write tests."""
    client = ModbusTcpClient(modbus_host, port=modbus_port)
    client.connect()
    logger.info(f"Modbus client connected: {modbus_host}:{modbus_port}")

    passed = 0
    failed = 0

    try:
        # === Test 1: Read coils (initial values should be False) ===
        logger.info("\n=== Test 1: Read coils (initial) ===")
        rr = client.read_coils(address=1, count=18, device_id=slave_id)
        if not rr.isError():
            logger.info(f"Coils 1-18: {rr.bits[:18]}")
            if all(v == False for v in rr.bits[:18]):
                logger.info("  PASS: all coils initially False")
                passed += 1
            else:
                logger.error("  FAIL: some coils not False")
                failed += 1
        else:
            logger.error(f"  ERROR: {rr}")
            failed += 1

        # === Test 2: Write coil and verify ===
        logger.info("\n=== Test 2: Write coil 1 (Proces.BoxReady_AM68) ===")
        ww = client.write_coil(address=1, value=True, device_id=slave_id)
        if not ww.isError():
            logger.info("  Write OK")
        else:
            logger.error(f"  Write ERROR: {ww}")
            failed += 1
            return passed, failed

        time.sleep(0.5)

        rr = client.read_coils(address=1, count=1, device_id=slave_id)
        if not rr.isError() and rr.bits[0] == True:
            logger.info("  PASS: coil 1 = True")
            passed += 1
        else:
            logger.error(f"  FAIL: coil 1 = {rr.bits[0] if not rr.isError() else 'error'}")
            failed += 1

        # === Test 3: Read holding registers (initial values) ===
        logger.info("\n=== Test 3: Read holding registers (initial) ===")
        rr = client.read_holding_registers(address=1, count=4, device_id=slave_id)
        if not rr.isError():
            logger.info(f"HR 1-4: {rr.registers}")
            if rr.registers == [1, 1, 1, 1]:
                logger.info("  PASS: HR 1-4 all = 1")
                passed += 1
            else:
                logger.error(f"  FAIL: expected [1,1,1,1], got {rr.registers}")
                failed += 1
        else:
            logger.error(f"  ERROR: {rr}")
            failed += 1

        # === Test 4: Write holding register ===
        logger.info("\n=== Test 4: Write HR 2 (B.robWarningCode_R1) = 99 ===")
        ww = client.write_register(address=2, value=99, device_id=slave_id)
        if not ww.isError():
            logger.info("  Write OK")
        else:
            logger.error(f"  Write ERROR: {ww}")
            failed += 1
            return passed, failed

        time.sleep(0.5)

        rr = client.read_holding_registers(address=2, count=1, device_id=slave_id)
        if not rr.isError() and rr.registers[0] == 99:
            logger.info("  PASS: HR 2 = 99")
            passed += 1
        else:
            logger.error(f"  FAIL: HR 2 = {rr.registers[0] if not rr.isError() else 'error'}")
            failed += 1

        # === Test 5: Write multiple coils ===
        logger.info("\n=== Test 5: Write multiple coils ===")
        client.write_coil(address=3, value=True, device_id=slave_id)  # AM71
        client.write_coil(address=5, value=True, device_id=slave_id)  # AM72
        time.sleep(0.5)

        rr = client.read_coils(address=1, count=18, device_id=slave_id)
        if not rr.isError():
            expected = [True, False, True, False, True, False, False, False,
                        False, False, False, False, False, False, False, False, False, False]
            actual = rr.bits[:18]
            if actual == expected:
                logger.info("  PASS: coils match expected pattern")
                passed += 1
            else:
                logger.error(f"  FAIL: expected {expected}, got {actual}")
                failed += 1
        else:
            logger.error(f"  ERROR: {rr}")
            failed += 1

    finally:
        client.close()

    return passed, failed


async def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'kuka_mapping.yaml')
    config = load_config(config_path)

    ads_server = None
    ads_client = None
    modbus_slave = None
    mapper = None

    try:
        # 1. Start KUKA ADS Server
        ads_server = start_kuka_ads_server()
        logger.info("KUKA ADS Server started")
        time.sleep(1)

        # 2. Connect ADS Client
        ads_client = ADSClient(
            config['ads_connection']['ams_net_id'],
            config['ads_connection']['port']
        )
        ads_client.connect()
        logger.info("ADS Client connected")

        # 3. Start Modbus Slave
        modbus_slave = ModbusSlave(
            config['modbus_slave']['host'],
            config['modbus_slave']['port'],
            config['modbus_slave']['slave_id']
        )
        modbus_slave.setup_datastore(config['mappings'])

        # 4. Start DataMapper with bidirectional sync
        sync_interval = config.get('sync_interval', 1.0)
        mapper = DataMapper(ads_client, modbus_slave, config['mappings'], sync_interval)
        modbus_slave.set_write_callback(mapper.on_modbus_write)

        # 5. Start Modbus server and sync in background
        server_task = asyncio.create_task(modbus_slave.start())
        sync_task = asyncio.create_task(mapper.start_sync())

        # Wait for server to start
        await asyncio.sleep(1)
        logger.info("Modbus Slave started, running tests...")

        # 6. Run Modbus client tests
        passed, failed = test_modbus_operations(
            config['modbus_slave']['host'],
            config['modbus_slave']['port'],
            config['modbus_slave']['slave_id']
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"Test Results: {passed} passed, {failed} failed")
        logger.info(f"{'='*60}")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        if mapper:
            mapper.stop()
        if ads_client:
            ads_client.disconnect()
        if ads_server:
            ads_server.stop()
        logger.info("All services stopped")


if __name__ == "__main__":
    asyncio.run(main())
