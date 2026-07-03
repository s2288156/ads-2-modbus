import argparse
import asyncio
import logging
import signal
import sys

import pyads
from src.ads_client import ADSClient
from src.modbus_slave import ModbusSlave
from src.data_mapper import DataMapper
from src.log_config import setup_logging

logger = logging.getLogger(__name__)

# 支持的 data_type 列表
SUPPORTED_DATA_TYPES = {'bool', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'float', 'string'}
SUPPORTED_MODBUS_TYPES = {'coils', 'discrete_inputs', 'holding_registers', 'input_registers'}


def load_config(config_path):
    import yaml
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Config file parse error: {e}")
        raise


def validate_config(config):
    errors = []

    # ads_connection
    ads = config.get('ads_connection', {})
    if not ads.get('ams_net_id'):
        errors.append("ads_connection.ams_net_id is required")
    else:
        parts = ads['ams_net_id'].split('.')
        if len(parts) != 6 or not all(p.isdigit() for p in parts):
            errors.append(f"ads_connection.ams_net_id format invalid: {ads['ams_net_id']} (expected x.x.x.x.x.x)")

    port = ads.get('port', 48898)
    if not (1 <= port <= 65535):
        errors.append(f"ads_connection.port out of range: {port}")

    # modbus_slave
    mb = config.get('modbus_slave', {})
    if not mb.get('host'):
        errors.append("modbus_slave.host is required")
    mb_port = mb.get('port', 502)
    if not (1 <= mb_port <= 65535):
        errors.append(f"modbus_slave.port out of range: {mb_port}")

    # mappings
    mappings = config.get('mappings', [])
    if not mappings:
        errors.append("mappings is empty")

    for i, m in enumerate(mappings):
        prefix = f"mappings[{i}]"
        if not m.get('ads_var'):
            errors.append(f"{prefix}.ads_var is required")
        if not m.get('modbus_type') or m['modbus_type'] not in SUPPORTED_MODBUS_TYPES:
            errors.append(f"{prefix}.modbus_type invalid: {m.get('modbus_type')}")
        if not m.get('modbus_address') and m['modbus_address'] != 0:
            errors.append(f"{prefix}.modbus_address is required")
        if not m.get('data_type') or m['data_type'] not in SUPPORTED_DATA_TYPES:
            errors.append(f"{prefix}.data_type unsupported: {m.get('data_type')}")

    if errors:
        for e in errors:
            logger.error(f"Config validation: {e}")
        raise ValueError(f"Config validation failed with {len(errors)} error(s)")


async def main():
    parser = argparse.ArgumentParser(description='ADS to Modbus Gateway')
    parser.add_argument('--config', default='config/mapping.yaml', help='Mapping config file')
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    setup_logging(config)
    logger = logging.getLogger(__name__)

    try:
        validate_config(config)
    except ValueError as e:
        logger.error(str(e))
        return

    logger.info(f"Starting ADS to Modbus gateway (config: {args.config})")

    # Print local AMS Net ID for debugging
    ads_cfg = config['ads_connection']
    configured_local_ams = ads_cfg.get('local_ams_net_id') or '(not set)'
    try:
        pyads.open_port()
        actual_local_ams = pyads.get_local_address()
        actual_local_ams_id = f"{actual_local_ams.netid}:{actual_local_ams.port}"
    except Exception as e:
        logger.warning(f"Failed to get local AMS Net ID: {e}")
        actual_local_ams_id = "unknown"
    logger.info(f"Local AMS Net ID - configured: {configured_local_ams}, actual: {actual_local_ams_id}")

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        loop.call_soon_threadsafe(shutdown_event.set)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    ads_client = None
    modbus_slave = None
    mapper = None
    server_task = None
    sync_task = None
    shutdown_task = None

    try:
        ads_client = ADSClient(
            ams_net_id=ads_cfg['ams_net_id'],
            port=ads_cfg['port'],
            local_ams_net_id=ads_cfg.get('local_ams_net_id'),
            route_ip=ads_cfg.get('route_ip'),
            timeout=ads_cfg.get('timeout', 5000),
            reconnect_enabled=ads_cfg.get('reconnect_enabled', True),
            reconnect_interval=ads_cfg.get('reconnect_interval', 1.0),
            reconnect_max_interval=ads_cfg.get('reconnect_max_interval', 30.0),
            reconnect_backoff=ads_cfg.get('reconnect_backoff', 2.0),
            heartbeat_interval=config.get('heartbeat', {}).get('interval', 5),
            heartbeat_max_failures=config.get('heartbeat', {}).get('max_failures', 3),
            fallback_to_route_ip=ads_cfg.get('fallback_to_route_ip', True),
        )
        # 不做同步连接，Modbus 服务先启动，ADS 在后台持续重试
        logger.info("ADS not connected yet, will retry in background")

        mb_cfg = config['modbus_slave']
        modbus_slave = ModbusSlave(
            mb_cfg['host'],
            mb_cfg['port'],
            mb_cfg['slave_id'],
            max_connections=mb_cfg.get('max_connections', 10),
        )
        modbus_slave.setup_datastore(config['mappings'])
        logger.info("Modbus slave datastore initialized")

        sync_interval = config.get('sync_interval', 1.0)
        mapper = DataMapper(ads_client, modbus_slave, config['mappings'], sync_interval)
        modbus_slave.set_write_callback(mapper.on_modbus_write)
        logger.info(f"Data sync service started, interval: {sync_interval}s")

        # 运行任务 + 关闭等待
        server_task = asyncio.create_task(modbus_slave.start())
        sync_task = asyncio.create_task(mapper.start_sync())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        done, pending = await asyncio.wait(
            [server_task, sync_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # 检查是否有异常
        for task in done:
            if task.exception():
                logger.error(f"Task failed: {task.exception()}")

    except Exception as e:
        logger.error(f"Gateway runtime error: {e}", exc_info=True)
    finally:
        logger.info("Shutting down gateway...")

        if mapper:
            mapper.stop()
        if modbus_slave:
            await modbus_slave.stop()
        if ads_client:
            ads_client.disconnect()

        # 取消残留任务
        for t in [server_task, sync_task, shutdown_task]:
            if t and not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass

        logger.info("Gateway stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("User interrupted, gateway stopped")
