import logging
from pymodbus.server import StartAsyncTcpServer
from pymodbus import ModbusDeviceIdentification
from pymodbus.simulator import SimDevice, SimData, DataType

logger = logging.getLogger(__name__)

class ModbusSlave:
    def __init__(self, host, port, slave_id):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.device = None
        self.di_data = [0] * 100
        self.co_data = [0] * 100
        self.hr_data = [0] * 100
        self.ir_data = [0] * 100
        self.write_callback = None
    
    def set_write_callback(self, callback):
        self.write_callback = callback
    
    async def data_action(self, *args, **kwargs):
        fc = args[0]
        if fc == 3:
            return self.hr_data
        elif fc == 4:
            return self.ir_data
        elif fc == 1:
            return self.co_data
        elif fc == 2:
            return self.di_data
        elif fc == 6:
            addr = args[2]
            values = args[5]
            if values is not None and len(values) > 0:
                value = values[0]
                if 0 <= addr - 1 < len(self.hr_data):
                    self.hr_data[addr - 1] = value
                    logger.info(f"Modbus write: holding_registers[{addr}] = {value}")
                    if self.write_callback:
                        await self.write_callback('holding_registers', addr, value)
        elif fc == 5:
            addr = args[2]
            values = args[5]
            if values is not None and len(values) > 0:
                value = values[0]
                if 0 <= addr - 1 < len(self.co_data):
                    self.co_data[addr - 1] = value
                    logger.info(f"Modbus write: coils[{addr}] = {value}")
                    if self.write_callback:
                        await self.write_callback('coils', addr, value)
        elif fc == 16:
            addr = args[2]
            values = args[5]
            if values is not None:
                for i, v in enumerate(values):
                    if 0 <= addr - 1 + i < len(self.hr_data):
                        self.hr_data[addr - 1 + i] = v
                        logger.info(f"Modbus write: holding_registers[{addr + i}] = {v}")
                        if self.write_callback:
                            await self.write_callback('holding_registers', addr + i, v)
        elif fc == 15:
            addr = args[2]
            values = args[5]
            if values is not None:
                for i, v in enumerate(values):
                    if 0 <= addr - 1 + i < len(self.co_data):
                        self.co_data[addr - 1 + i] = v
                        logger.info(f"Modbus write: coils[{addr + i}] = {v}")
                        if self.write_callback:
                            await self.write_callback('coils', addr + i, v)
        return []
    
    def setup_datastore(self, mappings=None):
        di = SimData(1, count=100, values=self.di_data, datatype=DataType.BITS)
        co = SimData(1, count=100, values=self.co_data, datatype=DataType.BITS)
        hr = SimData(1, count=100, values=self.hr_data, datatype=DataType.REGISTERS)
        ir = SimData(1, count=100, values=self.ir_data, datatype=DataType.REGISTERS)
        
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'ADS-2-Modbus Gateway'
        identity.ProductName = 'ADS to Modbus Gateway'
        identity.ModelName = 'Gateway v1.0'
        identity.MajorMinorRevision = '1.0'
        
        self.device = SimDevice(
            id=self.slave_id,
            simdata=([di], [co], [hr], [ir]),
            identity=identity,
            action=self.data_action
        )
        logger.info("Modbus datastore initialized")
    
    async def start(self):
        logger.info(f"Starting Modbus TCP server: {self.host}:{self.port}")
        await StartAsyncTcpServer(
            context=self.device,
            address=(self.host, self.port)
        )
    
    def update_register(self, register_type, address, value):
        address_idx = address - 1
        
        if register_type == 'discrete_inputs':
            if 0 <= address_idx < len(self.di_data):
                self.di_data[address_idx] = value
                if self.device:
                    self.device.simdata[1][0].values = self.di_data.copy()
                logger.debug(f"Updated discrete_inputs[{address}] = {value}")
        elif register_type == 'coils':
            if 0 <= address_idx < len(self.co_data):
                self.co_data[address_idx] = value
                if self.device:
                    self.device.simdata[0][0].values = self.co_data.copy()
                logger.debug(f"Updated coils[{address}] = {value}")
        elif register_type == 'holding_registers':
            if 0 <= address_idx < len(self.hr_data):
                self.hr_data[address_idx] = value
                if self.device:
                    self.device.simdata[2][0].values = self.hr_data.copy()
                logger.debug(f"Updated holding_registers[{address}] = {value}")
        elif register_type == 'input_registers':
            if 0 <= address_idx < len(self.ir_data):
                self.ir_data[address_idx] = value
                if self.device:
                    self.device.simdata[3][0].values = self.ir_data.copy()
                logger.debug(f"Updated input_registers[{address}] = {value}")
        else:
            logger.error(f"Unknown register type: {register_type}")