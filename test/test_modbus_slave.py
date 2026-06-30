import asyncio
import logging
from pymodbus.server import StartAsyncTcpServer
from pymodbus import ModbusDeviceIdentification
from pymodbus.constants import ExcCodes
from pymodbus.simulator import SimDevice, SimData, DataType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

FC_NAMES = {
    1: "Read Coils (0x01)",
    2: "Read Discrete Inputs (0x02)",
    3: "Read Holding Registers (0x03)",
    4: "Read Input Registers (0x04)",
    5: "Write Single Coil (0x05)",
    6: "Write Single Register (0x06)",
    15: "Write Multiple Coils (0x0F)",
    16: "Write Multiple Registers (0x10)",
}

# SimDevice action 参数:
#   function_code:   int                      功能码
#   start_address:   int                      current_registers[0] 的绝对地址
#   address:         int                      请求地址
#   count:           int                      读取数量 / 写入数量
#   current_registers: list[int]              寄存器数组 (就地修改生效)
#   set_values:      list[int]|list[bool]|None  写请求的值 (读请求为 None)


class InterceptedModbusSlave:
    """Modbus Slave 单文件服务，拦截并打印所有读写操作。

    通过 pymodbus SimDevice 的 action 回调拦截请求。
    拦截钩子 on_read / on_write 可以被子类重写以添加自定义操作。
    """

    def __init__(self, host="0.0.0.0", port=5020, slave_id=1):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.device = None

    # ------------------------------------------------------------------
    # 拦截回调 —— SimDevice action 入口
    # ------------------------------------------------------------------
    async def data_action(
        self,
        function_code: int,
        start_address: int,
        address: int,
        count: int,
        current_registers: list[int],
        set_values: list[int] | list[bool] | None,
    ):
        fc_name = FC_NAMES.get(function_code, f"Unknown FC={function_code}")

        if function_code in (1, 2, 3, 4):
            self._on_read(function_code, fc_name, start_address, address, count, current_registers)
        elif function_code in (5, 6, 15, 16):
            self._on_write(function_code, fc_name, start_address, address, current_registers, set_values)
        else:
            logger.warning(f"未处理: {fc_name}")

    def _on_read(self, fc, fc_name, start_address, address, count, current_registers):
        offset = address - start_address
        values = current_registers[offset:offset + count]
        logger.info(f"[READ] {fc_name} | addr={address} count={count} => {values}")
        self.on_read(fc, address, count, values)

    def _on_write(self, fc, fc_name, start_address, address, current_registers, set_values):
        if not set_values:
            return
        offset = address - start_address
        if fc in (5, 15):
            for i, v in enumerate(set_values):
                idx = offset + i
                if 0 <= idx < len(current_registers):
                    current_registers[idx] = int(v)
            logger.info(f"[WRITE] {fc_name} | addr={address} value={set_values}")
            self.on_write("coils", address, set_values)
        elif fc in (6, 16):
            for i, v in enumerate(set_values):
                idx = offset + i
                if 0 <= idx < len(current_registers):
                    current_registers[idx] = v
            logger.info(f"[WRITE] {fc_name} | addr={address} value={set_values}")
            self.on_write("holding_registers", address, set_values)

    # ------------------------------------------------------------------
    # 可扩展的钩子 —— 重写这些方法添加自定义操作
    # ------------------------------------------------------------------
    def on_read(self, fc, address, count, values):
        """读操作拦截钩子。

        Args:
            fc: 功能码 (1=Coils, 2=DI, 3=HR, 4=IR)
            address: 起始地址
            count: 读取数量
            values: 读到的值列表
        """

    def on_write(self, reg_type, address, value):
        """写操作拦截钩子。

        Args:
            reg_type: "coils" | "holding_registers"
            address: 起始地址
            value: 写入值 (单写为 int, 多写为 list)
        """

    # ------------------------------------------------------------------
    # 初始化和启动
    # ------------------------------------------------------------------
    def setup(self):
        hr_block = SimData(address=0, count=100, values=0, datatype=DataType.REGISTERS)
        co_block = SimData(address=0, count=100, values=False, datatype=DataType.BITS)
        di_block = SimData(address=0, count=100, values=False, datatype=DataType.BITS)
        ir_block = SimData(address=0, count=100, values=0, datatype=DataType.REGISTERS)

        identity = ModbusDeviceIdentification()
        identity.VendorName = "Test Modbus Slave"
        identity.ProductName = "Modbus Slave Interceptor"
        identity.ModelName = "Interceptor v1.0"
        identity.MajorMinorRevision = "1.0"

        self.device = SimDevice(
            id=self.slave_id,
            simdata=([co_block], [di_block], [hr_block], [ir_block]),
            identity=identity,
            action=self.data_action,
        )
        logger.info("数据存储初始化完成 (100 HR, 100 CO, 100 DI, 100 IR)")

    async def start(self):
        logger.info(f"Modbus Slave 启动 => {self.host}:{self.port}  Slave ID={self.slave_id}")
        await StartAsyncTcpServer(
            context=self.device,
            address=(self.host, self.port),
        )


if __name__ == "__main__":
    slave = InterceptedModbusSlave(host="0.0.0.0", port=5020, slave_id=1)
    slave.setup()

    logger.info("=" * 60)
    logger.info("Modbus Slave 拦截服务就绪")
    logger.info("等待 Master 连接，所有读写操作将打印到控制台")
    logger.info("在 on_read / on_write 方法中可添加自定义操作")
    logger.info("按 Ctrl+C 停止")
    logger.info("=" * 60)

    try:
        asyncio.run(slave.start())
    except KeyboardInterrupt:
        logger.info("服务已停止")
