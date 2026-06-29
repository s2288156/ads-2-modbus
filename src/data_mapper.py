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
    
    def ads_to_modbus_value(self, value, data_type):
        if data_type == 'bool':
            return 1 if value else 0
        elif data_type == 'int':
            return int(value)
        elif data_type == 'float':
            packed = struct.pack('!f', float(value))
            return [int.from_bytes(packed[i:i+2], 'big') for i in [0, 2]]
        elif data_type == 'int16':
            return int(value) & 0xFFFF
        elif data_type == 'int32':
            return int(value)
        else:
            logger.warning(f"Unsupported data type: {data_type}")
            return int(value)
    
    def modbus_to_ads_value(self, value, data_type):
        if data_type == 'bool':
            return bool(value)
        elif data_type == 'int' or data_type == 'int16':
            return int(value)
        elif data_type == 'int32':
            return int(value)
        elif data_type == 'float':
            if isinstance(value, list) and len(value) >= 2:
                packed = bytes([(value[0] >> 8) & 0xFF, value[0] & 0xFF,
                               (value[1] >> 8) & 0xFF, value[1] & 0xFF])
                return struct.unpack('!f', packed)[0]
            else:
                return float(value)
        else:
            logger.warning(f"Unsupported data type: {data_type}")
            return value
    
    async def sync_ads_to_modbus(self):
        for mapping in self.mappings:
            try:
                ads_value = self.ads_client.read_by_name(mapping['ads_var'])
                modbus_value = self.ads_to_modbus_value(ads_value, mapping['data_type'])
                
                if isinstance(modbus_value, list):
                    for i, v in enumerate(modbus_value):
                        self.modbus_slave.update_register(
                            mapping['modbus_type'],
                            mapping['modbus_address'] + i,
                            v
                        )
                else:
                    self.modbus_slave.update_register(
                        mapping['modbus_type'],
                        mapping['modbus_address'],
                        modbus_value
                    )
            except Exception as e:
                logger.error(f"Failed to sync ADS variable {mapping['ads_var']}: {e}")
    
    async def sync_modbus_to_ads(self):
        for mapping in self.mappings:
            try:
                modbus_value = self.modbus_slave.read_register(
                    mapping['modbus_type'],
                    mapping['modbus_address']
                )
                
                if modbus_value is not None:
                    ads_value = self.modbus_to_ads_value(modbus_value, mapping['data_type'])
                    self.ads_client.write_by_name(mapping['ads_var'], ads_value)
            except Exception as e:
                logger.error(f"Failed to sync Modbus to ADS variable {mapping['ads_var']}: {e}")
    
    async def start_sync(self):
        self.running = True
        logger.info(f"Data sync service started, interval: {self.sync_interval}s")
        
        await self.sync_ads_to_modbus()
        logger.info("Initial sync ADS to Modbus completed")
        
        while self.running:
            await asyncio.sleep(self.sync_interval)
    
    async def on_modbus_write(self, register_type, address, value):
        for mapping in self.mappings:
            if mapping['modbus_type'] == register_type and mapping['modbus_address'] == address:
                try:
                    ads_value = self.modbus_to_ads_value(value, mapping['data_type'])
                    self.ads_client.write_by_name(mapping['ads_var'], ads_value)
                    logger.info(f"Synced Modbus write to ADS: {mapping['ads_var']} = {ads_value}")
                except Exception as e:
                    logger.error(f"Failed to sync Modbus write to ADS: {e}")
    
    def stop(self):
        self.running = False
        logger.info("Data sync service stopped")