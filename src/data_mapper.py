import asyncio
import logging
import struct

logger = logging.getLogger(__name__)

class DataMapper:
    def __init__(self, ads_client, modbus_slave, mappings, sync_interval=1.0):
        self.ads_client = ads_client
        self.modbus_slave = modbus_slave
        self.mappings = mappings
        self.sync_interval = sync_interval
        self.running = False
        self._dirty_from_modbus = set()

    def get_register_count(self, data_type):
        if data_type in ['int32', 'uint32', 'float']:
            return 2
        return 1

    def ads_to_modbus_value(self, value, data_type):
        if data_type == 'bool':
            return 1 if value else 0
        elif data_type in ('int', 'int16'):
            return int(value) & 0xFFFF
        elif data_type == 'uint16':
            return int(value) & 0xFFFF
        elif data_type == 'uint8':
            return int(value) & 0xFF
        elif data_type == 'int32':
            packed = struct.pack('!i', int(value))
            return [int.from_bytes(packed[i:i+2], 'big') for i in [0, 2]]
        elif data_type == 'uint32':
            packed = struct.pack('!I', int(value))
            return [int.from_bytes(packed[i:i+2], 'big') for i in [0, 2]]
        elif data_type == 'float':
            packed = struct.pack('!f', float(value))
            return [int.from_bytes(packed[i:i+2], 'big') for i in [0, 2]]
        else:
            logger.warning(f"Unsupported data type: {data_type}")
            return int(value)

    def modbus_to_ads_value(self, value, data_type):
        if data_type == 'bool':
            return bool(value)
        elif data_type in ('int', 'int16'):
            return int(value)
        elif data_type == 'uint16':
            return int(value) & 0xFFFF
        elif data_type == 'uint8':
            return int(value) & 0xFF
        elif data_type == 'int32':
            if isinstance(value, list) and len(value) >= 2:
                packed = bytes([(value[0] >> 8) & 0xFF, value[0] & 0xFF,
                               (value[1] >> 8) & 0xFF, value[1] & 0xFF])
                return struct.unpack('!i', packed)[0]
            return int(value)
        elif data_type == 'uint32':
            if isinstance(value, list) and len(value) >= 2:
                packed = bytes([(value[0] >> 8) & 0xFF, value[0] & 0xFF,
                               (value[1] >> 8) & 0xFF, value[1] & 0xFF])
                return struct.unpack('!I', packed)[0]
            return int(value)
        elif data_type == 'float':
            if isinstance(value, list) and len(value) >= 2:
                packed = bytes([(value[0] >> 8) & 0xFF, value[0] & 0xFF,
                               (value[1] >> 8) & 0xFF, value[1] & 0xFF])
                return struct.unpack('!f', packed)[0]
            return float(value)
        else:
            logger.warning(f"Unsupported data type: {data_type}")
            return value

    async def sync_ads_to_modbus(self):
        try:
            await self.ads_client.ensure_connected()
        except ConnectionError:
            logger.warning("ADS not connected, skipping sync")
            return

        for i, mapping in enumerate(self.mappings):
            if i in self._dirty_from_modbus:
                self._dirty_from_modbus.discard(i)
                logger.debug(f"Skipping ADS->Modbus sync for {mapping['ads_var']} (dirty from Modbus)")
                continue

            try:
                index_group = mapping['index_group']
                index_offset = mapping['index_offset']
                plc_datatype = self.ads_client.get_plc_datatype(mapping['data_type'])
                ads_value = self.ads_client.read_by_address(index_group, index_offset, plc_datatype)
                modbus_value = self.ads_to_modbus_value(ads_value, mapping['data_type'])

                if isinstance(modbus_value, list):
                    for j, v in enumerate(modbus_value):
                        self.modbus_slave.update_register(
                            mapping['modbus_type'],
                            mapping['modbus_address'] + j,
                            v
                        )
                else:
                    self.modbus_slave.update_register(
                        mapping['modbus_type'],
                        mapping['modbus_address'],
                        modbus_value
                    )
                logger.debug(f"Synced ADS 0x{index_group:X}:{index_offset} ({ads_value}) -> Modbus {mapping['modbus_type']}[{mapping['modbus_address']}]")
            except Exception as e:
                logger.error(f"Failed to sync ADS variable {mapping['ads_var']}: {e}")

    async def sync_modbus_to_ads(self):
        try:
            await self.ads_client.ensure_connected()
        except ConnectionError:
            logger.warning("ADS not connected, skipping Modbus->ADS sync")
            return

        for mapping in self.mappings:
            try:
                register_count = self.get_register_count(mapping['data_type'])

                if register_count > 1:
                    modbus_values = []
                    for j in range(register_count):
                        value = self.modbus_slave.read_register(
                            mapping['modbus_type'],
                            mapping['modbus_address'] + j
                        )
                        modbus_values.append(value if value is not None else 0)
                    modbus_value = modbus_values
                else:
                    modbus_value = self.modbus_slave.read_register(
                        mapping['modbus_type'],
                        mapping['modbus_address']
                    )

                if modbus_value is not None:
                    ads_value = self.modbus_to_ads_value(modbus_value, mapping['data_type'])
                    index_group = mapping['index_group']
                    index_offset = mapping['index_offset']
                    plc_datatype = self.ads_client.get_plc_datatype(mapping['data_type'])
                    self.ads_client.write_by_address(index_group, index_offset, ads_value, plc_datatype)
                    logger.debug(f"Synced Modbus {mapping['modbus_type']}[{mapping['modbus_address']}] -> ADS 0x{index_group:X}:{index_offset} ({ads_value})")
            except Exception as e:
                logger.error(f"Failed sync Modbus->ADS {mapping['ads_var']}: {e}")

    async def start_sync(self):
        self.running = True
        logger.info(f"Data sync service started, interval: {self.sync_interval}s")

        # 等待 ADS 连接成功（后台持续重试）
        while self.running and not self.ads_client.connected:
            try:
                await self.ads_client.ensure_connected()
            except ConnectionError:
                await asyncio.sleep(5)

        if not self.running:
            return

        logger.info("ADS connected, starting data sync")

        # 首次连接成功后启动心跳
        if not self.ads_client._heartbeat_task or self.ads_client._heartbeat_task.done():
            self.ads_client.start_heartbeat()

        await self.sync_ads_to_modbus()
        logger.info("Initial sync ADS->Modbus completed")

        while self.running:
            await asyncio.sleep(self.sync_interval)
            await self.sync_ads_to_modbus()

    async def on_modbus_write(self, register_type, address, value):
        for i, mapping in enumerate(self.mappings):
            if mapping['modbus_type'] != register_type:
                continue

            register_count = self.get_register_count(mapping['data_type'])

            if register_count > 1:
                start_addr = mapping['modbus_address']
                end_addr = start_addr + register_count - 1
                if start_addr <= address <= end_addr:
                    self._dirty_from_modbus.add(i)
                    await self._write_single_to_ads(mapping, register_type, address, value)
                    return
            else:
                if mapping['modbus_address'] == address:
                    self._dirty_from_modbus.add(i)
                    await self._write_single_to_ads(mapping, register_type, address, value)
                    return

    async def _write_single_to_ads(self, mapping, register_type, address, value):
        try:
            await self.ads_client.ensure_connected()
            ads_value = self.modbus_to_ads_value(value, mapping['data_type'])
            index_group = mapping['index_group']
            index_offset = mapping['index_offset']
            plc_datatype = self.ads_client.get_plc_datatype(mapping['data_type'])
            self.ads_client.write_by_address(index_group, index_offset, ads_value, plc_datatype)
            logger.info(f"Modbus write -> ADS: {mapping['ads_var']} = {ads_value} (0x{index_group:X}:{index_offset})")
        except Exception as e:
            logger.error(f"Failed Modbus->ADS write for {mapping['ads_var']}: {e}")

    def stop(self):
        self.running = False
        logger.info("Data sync service stopped")
