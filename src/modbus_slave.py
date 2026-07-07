import asyncio
import logging
from pymodbus.server import StartAsyncTcpServer
from pymodbus import ModbusDeviceIdentification
from pymodbus.simulator import SimDevice, SimData, DataType

logger = logging.getLogger(__name__)

class ModbusSlave:
    def __init__(self, host, port, slave_id, max_connections=10):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.max_connections = max_connections
        self.device = None
        self.write_callback = None
        self.di_data = [0] * 100
        self.co_data = [0] * 100
        self.hr_data = [0] * 100
        self.ir_data = [0] * 100
        self._server = None

    def set_write_callback(self, callback):
        self.write_callback = callback

    async def data_action(
        self,
        function_code: int,
        start_address: int,
        address: int,
        count: int,
        current_registers: list[int],
        set_values: list[int] | list[bool] | None,
    ):
        if function_code in (1, 2):
            # Coils / Discrete inputs: pymodbus passes bit-level addresses,
            # must convert to register offset and pack bits correctly.
            src = self.co_data if function_code == 1 else self.di_data
            reg_start = int(address / 16) - start_address
            for i in range(count):
                reg_idx = reg_start + i
                if 0 <= reg_idx < len(current_registers):
                    reg_val = 0
                    for bit in range(16):
                        bit_addr = (start_address + reg_idx) * 16 + bit
                        data_idx = bit_addr - 1  # 1-based Modbus address -> 0-based array
                        if 0 <= data_idx < len(src) and src[data_idx]:
                            reg_val |= (1 << bit)
                    current_registers[reg_idx] = reg_val

        elif function_code in (3, 4):
            # Holding / Input registers: register-level addressing, straightforward copy.
            offset = address - start_address
            src = self.hr_data if function_code == 3 else self.ir_data
            for i in range(count):
                idx = offset + i
                if 0 <= idx < len(src) and idx < len(current_registers):
                    current_registers[idx] = src[idx]

        elif function_code in (5, 15) and set_values is not None:
            for i, v in enumerate(set_values):
                val = int(v)
                data_idx = address - 1 + i
                if 0 <= data_idx < len(self.co_data):
                    self.co_data[data_idx] = val
                    logger.info(f"Modbus write: coils[{address + i}] = {val}")
                    if self.write_callback:
                        await self.write_callback('coils', address + i, val)

        elif function_code in (6, 16) and set_values is not None:
            offset = address - start_address
            for i, v in enumerate(set_values):
                idx = offset + i
                if 0 <= idx < len(current_registers):
                    current_registers[idx] = v
                if 0 <= address - 1 + i < len(self.hr_data):
                    self.hr_data[address - 1 + i] = v
                    logger.info(f"Modbus write: holding_registers[{address + i}] = {v}")
                    if self.write_callback:
                        await self.write_callback('holding_registers', address + i, v)

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
        self._server = await StartAsyncTcpServer(
            context=self.device,
            address=(self.host, self.port),
        )
        logger.info("Modbus TCP server started")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Modbus TCP server stopped")

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

    def read_register(self, register_type, address):
        address_idx = address - 1

        if register_type == 'discrete_inputs':
            if 0 <= address_idx < len(self.di_data):
                return self.di_data[address_idx]
        elif register_type == 'coils':
            if 0 <= address_idx < len(self.co_data):
                return self.co_data[address_idx]
        elif register_type == 'holding_registers':
            if 0 <= address_idx < len(self.hr_data):
                return self.hr_data[address_idx]
        elif register_type == 'input_registers':
            if 0 <= address_idx < len(self.ir_data):
                return self.ir_data[address_idx]

        logger.error(f"Failed to read {register_type}[{address}]")
        return None
