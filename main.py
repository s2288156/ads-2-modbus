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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def load_config(config_path='config/mapping.yaml'):
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"配置文件未找到: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"配置文件解析错误: {e}")
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
                logger.info(f"Registered ADS variable: {var.name} -> type={var.symbol_type}, value={var.value}")
    
    handler = ADSHandler()
    server = AdsTestServer(handler, '127.0.0.1', 48898)
    logger.info("Starting ADS Test Server on 127.0.0.1:48898...")
    logger.info("AMS Net ID: 127.0.0.1.1.1")
    server.start()
    return server

async def main():
    logger.info("启动ADS到Modbus网关")
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return
    
    ads_server = None
    ads_client = None
    modbus_slave = None
    mapper = None
    
    try:
        ads_server = start_ads_test_server()
        logger.info("ADS测试服务器启动成功")
        
        time.sleep(1)
        
        ads_client = ADSClient(
            config['ads_connection']['ams_net_id'],
            config['ads_connection']['port']
        )
        ads_client.connect()
        logger.info("ADS客户端连接成功")
        
        modbus_slave = ModbusSlave(
            config['modbus_slave']['host'],
            config['modbus_slave']['port'],
            config['modbus_slave']['slave_id']
        )
        modbus_slave.setup_datastore(config['mappings'])
        logger.info("Modbus slave数据存储初始化成功")
        
        sync_interval = config.get('sync_interval', 1.0)
        mapper = DataMapper(ads_client, modbus_slave, config['mappings'], sync_interval)
        modbus_slave.set_write_callback(mapper.on_modbus_write)
        
        logger.info(f"数据同步服务启动，同步间隔: {sync_interval}s")
        
        server_task = asyncio.create_task(modbus_slave.start())
        sync_task = asyncio.create_task(mapper.start_sync())
        
        await asyncio.gather(server_task, sync_task)
        
    except Exception as e:
        logger.error(f"网关运行异常: {e}", exc_info=True)
    finally:
        if mapper:
            mapper.stop()
        if ads_client:
            ads_client.disconnect()
        if ads_server:
            ads_server.stop()
        logger.info("网关已停止")

def signal_handler(signal_num, frame):
    logger.info(f"收到信号 {signal_num}，正在停止网关...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断，网关已停止")