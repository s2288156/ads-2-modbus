import argparse
import asyncio
import logging
import yaml
import signal
import sys
import threading
import time

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

def start_ads_test_server():
    from pyads.testserver import AdsTestServer
    from pyads.testserver.advanced_handler import AdvancedHandler, PLCVariable
    from pyads import constants
    
    class ADSHandler(AdvancedHandler):
        def __init__(self):
            super().__init__()
            self._register_variables()
        
        def _register_variables(self):
            variables = [
                PLCVariable(
                    name='GVL.bool_value',
                    value=True,
                    ads_type=constants.ADST_BIT,
                    symbol_type='BOOL',
                    index_group=0x4020,
                    index_offset=0
                ),
                PLCVariable(
                    name='GVL.int_value',
                    value=1234,
                    ads_type=constants.ADST_INT32,
                    symbol_type='DINT',
                    index_group=0x4020,
                    index_offset=16
                ),
                PLCVariable(
                    name='GVL.int16_value',
                    value=5678,
                    ads_type=constants.ADST_INT16,
                    symbol_type='INT',
                    index_group=0x4020,
                    index_offset=20
                ),
                PLCVariable(
                    name='GVL.float_value',
                    value=3.14,
                    ads_type=constants.ADST_REAL32,
                    symbol_type='REAL',
                    index_group=0x4020,
                    index_offset=32
                ),
                PLCVariable(
                    name='GVL.uint16_value',
                    value=30000,
                    ads_type=constants.ADST_UINT16,
                    symbol_type='UINT',
                    index_group=0x4020,
                    index_offset=36
                ),
                PLCVariable(
                    name='GVL.usint_value',
                    value=255,
                    ads_type=constants.ADST_UINT8,
                    symbol_type='USINT',
                    index_group=0x4020,
                    index_offset=38
                ),
                PLCVariable(
                    name='GVL.uint32_value',
                    value=4294967295,
                    ads_type=constants.ADST_UINT32,
                    symbol_type='UDINT',
                    index_group=0x4020,
                    index_offset=40
                ),
            ]
            
            for var in variables:
                self.add_variable(var)
                logger.info(f"Registered ADS variable: {var.name:<32s} index_offset={var.index_offset:<6d} type={var.symbol_type:<6s} value={int.from_bytes(var.value, 'big') if isinstance(var.value, bytes) else var.value}")
    
    handler = ADSHandler()
    server = AdsTestServer(handler, '127.0.0.1', 48898)
    logger.info("Starting ADS Test Server on 127.0.0.1:48898...")
    logger.info("AMS Net ID: 127.0.0.1.1.1")
    server.start()
    return server

def start_kuka_ads_server():
    from pyads.testserver import AdsTestServer
    from pyads.testserver.advanced_handler import AdvancedHandler, PLCVariable
    from pyads import constants

    class ADSHandler(AdvancedHandler):
        def __init__(self):
            super().__init__()
            self._register_variables()

        def _register_variables(self):
            variables = [
                # --- BOOL Proces.* ---
                PLCVariable(name='Proces.BoxReady_AM46',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=6),
                PLCVariable(name='Proces.BoxReady_AM71',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=2),
                PLCVariable(name='Proces.PG_Full_Ready_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=17),
                PLCVariable(name='Proces.BoxReady_AM46_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=7),
                PLCVariable(name='Proces.PG_Box_Ready_cb', value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=15),
                PLCVariable(name='Proces.PG_Full_Ready',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=16),
                PLCVariable(name='Proces.BoxReady_AM72',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=4),
                PLCVariable(name='Proces.BoxReady_AM56',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=8),
                PLCVariable(name='Proces.BoxReady_AM58_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=11),
                PLCVariable(name='Proces.BoxReady_AM68_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=1),
                PLCVariable(name='Proces.BoxReady_AM59',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=12),
                PLCVariable(name='Proces.BoxReady_AM68',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=0),
                PLCVariable(name='Proces.BoxReady_AM72_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=5),
                PLCVariable(name='Proces.BoxReady_AM71_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=3),
                PLCVariable(name='Proces.BoxReady_AM58',   value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=10),
                PLCVariable(name='Proces.BoxReady_AM59_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=13),
                PLCVariable(name='Proces.PG_Full_End_cb',  value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=18),
                PLCVariable(name='Proces.BoxReady_AM56_cb',value=False, ads_type=constants.ADST_BIT, symbol_type='BOOL', index_group=0x4020, index_offset=9),
                # --- Robot 变量 ---
                PLCVariable(name='B.robWarningCode_R1',    value=1,     ads_type=constants.ADST_UINT16, symbol_type='UINT',  index_group=0x4020, index_offset=204),
                PLCVariable(name='B.batteryLevel_R1',      value=1,     ads_type=constants.ADST_UINT8,  symbol_type='USINT', index_group=0x4020, index_offset=200),
                PLCVariable(name='C.robWarningCode_R2',    value=1,     ads_type=constants.ADST_UINT16, symbol_type='UINT',  index_group=0x4020, index_offset=404),
                PLCVariable(name='C.batteryLevel_R2',      value=1,     ads_type=constants.ADST_UINT8,  symbol_type='USINT', index_group=0x4020, index_offset=400),
            ]

            for var in variables:
                self.add_variable(var)
                logger.info(f"Registered variable: {var.name:<32s} index_offset={var.index_offset:<6d} type={var.symbol_type:<6s} value={int.from_bytes(var.value, 'big') if isinstance(var.value, bytes) else var.value}")

    handler = ADSHandler()
    server = AdsTestServer(handler, '127.0.0.1', 48898)
    logger.info("Starting ADS Test Server on 127.0.0.1:48898...")
    logger.info("AMS Net ID: 127.0.0.1.1.1")
    server.start()
    return server

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

    ads_server = None
    ads_client = None
    modbus_slave = None
    mapper = None

    try:
        if 'kuka' in args.config:
            ads_server = start_kuka_ads_server()
        else:
            ads_server = start_ads_test_server()
        logger.info("ADS test server started successfully")
        
        time.sleep(1)
        
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
        if ads_server:
            ads_server.stop()
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