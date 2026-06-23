# ADS到Modbus网关实现方案

## 需求分析

用户需要实现一个协议转换网关，将ADS协议（Beckhoff TwinCAT）的Server端数据通过Modbus协议的Slave端提供给Modbus Master连接。

### 核心功能
- 从ADS Server读取数据
- 通过Modbus Slave暴露这些数据
- 支持Modbus Master的读写操作

## 推荐类库

### 1. ADS协议库 - pyads
- **名称**: pyads
- **版本**: 3.6.0+
- **用途**: 用于连接和通信Beckhoff TwinCAT设备
- **安装**: `pip install pyads`
- **特点**:
  - 支持Windows和Linux
  - 支持TwinCAT 2和TwinCAT 3
  - 支持按名称或地址读写变量
  - 支持设备通知回调

### 2. Modbus协议库 - pymodbus
- **名称**: pymodbus
- **版本**: 3.0.0+
- **用途**: 实现Modbus TCP/RTU Slave
- **安装**: `pip install pymodbus`
- **特点**:
  - 完整的Modbus协议实现
  - 支持TCP、UDP、RTU、ASCII
  - 支持同步和异步模式
  - 支持自定义数据存储

## 项目架构

### 整体架构
```
┌─────────────────┐      ADS协议      ┌─────────────────────┐
│  Beckhoff PLC   │ ←──────────────→ │      ADS Client     │
│  (ADS Server)   │                  │   (pyads库)         │
└─────────────────┘                  └──────────┬──────────┘
                                                │
                                                ▼
┌─────────────────┐      Modbus协议    ┌─────────────────────┐
│ Modbus Master   │ ←──────────────→ │     Modbus Slave    │
│  (客户端/上位机) │                  │    (pymodbus库)     │
└─────────────────┘                  └─────────────────────┘
```

### 组件说明

| 组件 | 职责 | 技术实现 |
|------|------|----------|
| ADS客户端 | 连接ADS Server，读取/写入数据 | pyads |
| 数据映射层 | 维护ADS变量与Modbus寄存器的映射关系 | Python字典/配置文件 |
| Modbus Slave | 提供Modbus服务，响应Master请求 | pymodbus |
| 数据同步层 | 同步ADS数据与Modbus寄存器 | 定时轮询/事件驱动 |

## 文件结构

```
ads-2-modbus/
├── venv/                    # Python虚拟环境
├── src/
│   ├── __init__.py
│   ├── ads_client.py        # ADS客户端封装
│   ├── modbus_slave.py      # Modbus Slave封装
│   ├── data_mapper.py       # 数据映射管理
│   └── config.py            # 配置管理
├── config/
│   └── mapping.yaml         # 变量映射配置
├── main.py                  # 主入口
├── requirements.txt         # 依赖列表
└── README.md                # 项目说明
```

## 关键实现步骤

### 步骤1：创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 步骤2：安装依赖

```bash
pip install pyads pymodbus pyyaml
```

### 步骤3：ADS客户端实现

```python
# src/ads_client.py
import pyads

class ADSClient:
    def __init__(self, ams_net_id, port):
        self.ams_net_id = ams_net_id
        self.port = port
        self.connection = None
    
    def connect(self):
        self.connection = pyads.Connection(self.ams_net_id, self.port)
        self.connection.open()
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
    
    def read_by_name(self, var_name, plc_datatype=None):
        return self.connection.read_by_name(var_name, plc_datatype)
    
    def write_by_name(self, var_name, value, plc_datatype=None):
        self.connection.write_by_name(var_name, value, plc_datatype)
```

### 步骤4：数据映射配置

```yaml
# config/mapping.yaml
# ADS变量到Modbus寄存器的映射配置
# 寄存器类型: holding_registers, input_registers, coils, discrete_inputs

ads_connection:
  ams_net_id: "127.0.0.1.1.1"
  port: 851

modbus_slave:
  host: "0.0.0.0"
  port: 502
  slave_id: 1

mappings:
  - ads_var: "GVL.int_value"
    modbus_type: "holding_registers"
    modbus_address: 0
    data_type: "int"
  
  - ads_var: "GVL.float_value"
    modbus_type: "holding_registers"
    modbus_address: 2
    data_type: "float"
  
  - ads_var: "GVL.bool_value"
    modbus_type: "coils"
    modbus_address: 0
    data_type: "bool"
```

### 步骤5：Modbus Slave实现

```python
# src/modbus_slave.py
from pymodbus.server.async_io import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

class ModbusSlave:
    def __init__(self, host, port, slave_id):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.store = None
        self.context = None
    
    def setup_datastore(self, mappings):
        # 初始化数据存储
        di = ModbusSequentialDataBlock(0, [0] * 100)
        co = ModbusSequentialDataBlock(0, [0] * 100)
        hr = ModbusSequentialDataBlock(0, [0] * 100)
        ir = ModbusSequentialDataBlock(0, [0] * 100)
        
        self.store = ModbusSlaveContext(di=di, co=co, hr=hr, ir=ir)
        self.context = ModbusServerContext(slaves={self.slave_id: self.store}, single=True)
    
    async def start(self):
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'ADS-2-Modbus Gateway'
        identity.ProductName = 'ADS to Modbus Gateway'
        identity.ModelName = 'Gateway v1.0'
        
        await StartAsyncTcpServer(
            context=self.context,
            identity=identity,
            address=(self.host, self.port)
        )
    
    def update_register(self, register_type, address, value):
        """更新寄存器值"""
        block = {
            'holding_registers': 'hr',
            'input_registers': 'ir',
            'coils': 'co',
            'discrete_inputs': 'di'
        }[register_type]
        self.store.setValues(block, address, [value])
```

### 步骤6：主程序整合

```python
# main.py
import asyncio
import yaml
from src.ads_client import ADSClient
from src.modbus_slave import ModbusSlave
from src.data_mapper import DataMapper

async def main():
    # 加载配置
    with open('config/mapping.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 初始化ADS客户端
    ads_client = ADSClient(
        config['ads_connection']['ams_net_id'],
        config['ads_connection']['port']
    )
    ads_client.connect()
    
    # 初始化Modbus Slave
    modbus_slave = ModbusSlave(
        config['modbus_slave']['host'],
        config['modbus_slave']['port'],
        config['modbus_slave']['slave_id']
    )
    modbus_slave.setup_datastore(config['mappings'])
    
    # 初始化数据映射器
    mapper = DataMapper(ads_client, modbus_slave, config['mappings'])
    
    # 启动Modbus服务器
    server_task = asyncio.create_task(modbus_slave.start())
    
    # 启动数据同步
    sync_task = asyncio.create_task(mapper.start_sync())
    
    await asyncio.gather(server_task, sync_task)

if __name__ == "__main__":
    asyncio.run(main())
```

## 依赖列表

```txt
# requirements.txt
pyads>=3.6.0
pymodbus>=3.0.0
pyyaml>=6.0
```

## 部署与运行

### 环境要求
- Python 3.9+
- Linux/Windows操作系统
- Beckhoff ADS Router (Linux需要额外安装)

### 运行步骤

1. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置映射文件**
编辑 `config/mapping.yaml`，配置ADS连接信息和变量映射

4. **启动网关**
```bash
python main.py
```

## 潜在风险与应对

### 风险1：ADS连接失败
- **原因**: PLC未运行、路由未配置、网络不通
- **应对**: 添加连接重试机制，增加日志记录

### 风险2：数据同步延迟
- **原因**: ADS读取耗时、网络延迟
- **应对**: 优化轮询频率，使用异步操作

### 风险3：数据类型转换错误
- **原因**: ADS变量类型与Modbus寄存器类型不匹配
- **应对**: 在映射配置中明确数据类型，添加转换验证

### 风险4：并发访问冲突
- **原因**: ADS读取和Modbus写入同时访问同一数据
- **应对**: 使用线程安全的数据存储，添加锁机制

## 扩展建议

1. **支持RTU模式**: 可扩展支持Modbus RTU协议
2. **历史数据记录**: 集成时序数据库存储历史数据
3. **Web管理界面**: 提供配置管理和状态监控
4. **告警功能**: 连接异常时发送通知
5. **多PLC支持**: 支持同时连接多个ADS Server

---

**文档版本**: v1.0  
**创建日期**: 2026-06-23