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
                logger.debug(f"Updated discrete_inputs[{address}] = {value}")
            else:
                logger.error(f"Address {address} out of range for discrete_inputs")
        elif register_type == 'coils':
            if 0 <= address_idx < len(self.co_data):
                self.co_data[address_idx] = value
                logger.debug(f"Updated coils[{address}] = {value}")
            else:
                logger.error(f"Address {address} out of range for coils")
        elif register_type == 'holding_registers':
            if 0 <= address_idx < len(self.hr_data):
                self.hr_data[address_idx] = value
                logger.debug(f"Updated holding_registers[{address}] = {value}")
            else:
                logger.error(f"Address {address} out of range for holding_registers")
        elif register_type == 'input_registers':
            if 0 <= address_idx < len(self.ir_data):
                self.ir_data[address_idx] = value
                logger.debug(f"Updated input_registers[{address}] = {value}")
            else:
                logger.error(f"Address {address} out of range for input_registers")
        else:
            logger.error(f"Unknown register type: {register_type}")
    
    def read_register(self, register_type, address):
        address_idx = address - 1
        
        if register_type == 'discrete_inputs':
            if 0 <= address_idx < len(self.di_data):
                return self.di_data[address_idx]
            else:
                logger.error(f"Address {address} out of range for discrete_inputs")
                return None
        elif register_type == 'coils':
            if 0 <= address_idx < len(self.co_data):
                return self.co_data[address_idx]
            else:
                logger.error(f"Address {address} out of range for coils")
                return None
        elif register_type == 'holding_registers':
            if 0 <= address_idx < len(self.hr_data):
                return self.hr_data[address_idx]
            else:
                logger.error(f"Address {address} out of range for holding_registers")
                return None
        elif register_type == 'input_registers':
            if 0 <= address_idx < len(self.ir_data):
                return self.ir_data[address_idx]
            else:
                logger.error(f"Address {address} out of range for input_registers")
                return None
        else:
            logger.error(f"Unknown register type: {register_type}")
            return None