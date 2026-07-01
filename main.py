import argparse
import asyncio
import logging
import yaml
import signal
import sys

from src.ads_client import ADSClient
from src.modbus_slave import ModbusSlave
from src.data_mapper import DataMapper
from src.log_config import setup_logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_path='config/mapping.yaml'):
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Config file parse error: {e}")
        raise

async def main():
    parser = argparse.ArgumentParser(description='ADS to Modbus Gateway')
    parser.add_argument('--config', default='config/kuka_mapping.yaml', help='Mapping config file')
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting ADS to Modbus gateway (config: {args.config})")

    ads_client = None
    modbus_slave = None
    mapper = None

    try:
        ads_client = ADSClient(
            config['ads_connection']['ams_net_id'],
            config['ads_connection']['port']
        )
        ads_client.connect()
        logger.info("ADS client connected successfully")

        modbus_slave = ModbusSlave(
            config['modbus_slave']['host'],
            config['modbus_slave']['port'],
            config['modbus_slave']['slave_id']
        )
        modbus_slave.setup_datastore(config['mappings'])
        logger.info("Modbus slave datastore initialized successfully")

        sync_interval = config.get('sync_interval', 1.0)
        mapper = DataMapper(ads_client, modbus_slave, config['mappings'], sync_interval)
        modbus_slave.set_write_callback(mapper.on_modbus_write)

        logger.info(f"Data sync service started, interval: {sync_interval}s")

        server_task = asyncio.create_task(modbus_slave.start())
        sync_task = asyncio.create_task(mapper.start_sync())

        await asyncio.gather(server_task, sync_task)

    except Exception as e:
        logger.error(f"Gateway runtime error: {e}", exc_info=True)
    finally:
        if mapper:
            mapper.stop()
        if ads_client:
            ads_client.disconnect()
        logger.info("Gateway stopped")

def signal_handler(signal_num, frame):
    logger.info(f"Received signal {signal_num}, stopping gateway...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("User interrupted, gateway stopped")