import asyncio
import threading
import time
import logging
import socket
import struct

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MockADSClient:
    def __init__(self, ams_net_id, port):
        self.ams_net_id = ams_net_id
        self.port = port
        self.connected = True
        self.variables = {
            'GVL.int_value': 1234,
            'GVL.int16_value': 5678,
            'GVL.uint16_value': 30000,
            'GVL.bool_value': True
        }

    def connect(self):
        self.connected = True
        logger.info(f"Mock ADS connected: {self.ams_net_id}:{self.port}")

    def disconnect(self):
        self.connected = False
        logger.info("Mock ADS connection closed")

    def read_by_name(self, var_name, plc_datatype=None):
        if var_name in self.variables:
            logger.debug(f"Mock ADS read: {var_name} = {self.variables[var_name]}")
            return self.variables[var_name]
        raise Exception(f"Variable {var_name} not found")

    def write_by_name(self, var_name, value, plc_datatype=None):
        if var_name in self.variables:
            self.variables[var_name] = value
            logger.info(f"Mock ADS write: {var_name} = {value}")
        else:
            raise Exception(f"Variable {var_name} not found")

async def start_gateway():
    from src.ads_client import ADSClient
    from src.modbus_slave import ModbusSlave
    from src.data_mapper import DataMapper
    import yaml

    with open('config/mapping.yaml', 'r') as f:
        config = yaml.safe_load(f)

    ads_client = MockADSClient(
        config['ads_connection']['ams_net_id'],
        config['ads_connection']['port']
    )
    ads_client.connect()

    modbus_slave = ModbusSlave(
        config['modbus_slave']['host'],
        config['modbus_slave']['port'],
        config['modbus_slave']['slave_id']
    )
    modbus_slave.setup_datastore(config['mappings'])

    sync_interval = config.get('sync_interval', 1.0)
    mapper = DataMapper(ads_client, modbus_slave, config['mappings'], sync_interval)

    server_task = asyncio.create_task(modbus_slave.start())
    sync_task = asyncio.create_task(mapper.start_sync())

    await asyncio.gather(server_task, sync_task)

def main():
    logger.info("Starting ADS to Modbus Gateway with Mock ADS Server...")

    try:
        asyncio.run(start_gateway())
    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal")
        logger.info("All services stopped")

if __name__ == "__main__":
    main()