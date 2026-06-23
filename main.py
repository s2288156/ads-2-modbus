import asyncio
import logging
import yaml
import signal
import sys

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

async def main():
    logger.info("启动ADS到Modbus网关")
    
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return
    
    ads_client = None
    modbus_slave = None
    mapper = None
    
    try:
        ads_client = ADSClient(
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
        
    except Exception as e:
        logger.error(f"网关运行异常: {e}", exc_info=True)
    finally:
        if mapper:
            mapper.stop()
        if ads_client:
            ads_client.disconnect()
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