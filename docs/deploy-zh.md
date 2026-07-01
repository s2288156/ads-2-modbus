# ADS to Modbus 网关 — 部署文档

## 概述

本项目是一个 ADS (Automation Device Specification) 到 Modbus TCP 的网关服务，用于将 Beckhoff/TwinCAT PLC 的 ADS 变量实时同步到 Modbus 寄存器，支持双向数据流。

## 环境要求

- Docker 及 Docker Compose
- Beckhoff PLC（运行 TwinCAT 3）且已开放 ADS 端口（默认 48898）

## 配置文件说明

配置文件位于 `config/mapping.yaml`，通过 Docker Compose 以只读方式挂载到容器内。

### 完整配置结构

```yaml
# ADS 连接配置
ads_connection:
  ams_net_id: "127.0.0.1.1.1"   # PLC 的 AMS Net ID（必填）
  port: 48898                    # ADS 端口号（默认 48898）
  local_ams_net_id: ""           # 本地 AMS Net ID（可选）
  route_ip: ""                   # PLC 的 IP 地址（可选，用于路由配置）
  timeout: 5000                  # ADS 操作超时，单位毫秒
  reconnect_enabled: true        # 是否启用自动重连
  reconnect_interval: 1.0        # 重连初始间隔（秒）
  reconnect_max_interval: 30.0   # 重连最大间隔（秒）
  reconnect_backoff: 2.0         # 重连退避倍数

# 心跳配置
heartbeat:
  interval: 5                    # 心跳检测间隔（秒）
  max_failures: 3                # 最大失败次数，超过后触发重连

# Modbus 从站配置
modbus_slave:
  host: "0.0.0.0"               # 监听地址（容器内固定 0.0.0.0）
  port: 5020                     # Modbus TCP 端口
  slave_id: 1                    # Modbus 从站 ID
  max_connections: 10            # 最大并发连接数

# 数据同步间隔（秒）
sync_interval: 0.5

# 日志配置
logging:
  log_dir: "/app/logs"           # 日志目录（容器内路径，通过 volume 挂载到宿主机）
  log_file: "gateway.log"        # 日志文件名
  level: "INFO"                  # 日志级别（DEBUG/INFO/WARNING/ERROR）
  max_bytes: 209715200           # 单个日志文件最大大小（200MB）
  max_days: 7                    # 日志保留天数
  max_total_bytes: 2147483648    # 日志总大小上限（2GB）
  backup_count: 7                # 日志备份数量
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 变量映射表
mappings:
  - ads_var: "Proces.BoxReady_AM68"     # ADS 变量名（PLC 中的完整路径）
    modbus_type: "coils"                 # Modbus 寄存器类型
    modbus_address: 1                    # Modbus 起始地址（从 1 开始）
    data_type: "bool"                    # 数据类型
    description: "BoxReady AM68"         # 描述（可选）
```

### 字段详解

#### `ads_connection` — ADS 连接参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `ams_net_id` | string | 是 | — | PLC 的 AMS Net ID，格式为 `x.x.x.x.x.x`（6 段数字，用点分隔） |
| `port` | int | 否 | 48898 | ADS 通信端口号 |
| `local_ams_net_id` | string | 否 | `""` | 本机 AMS Net ID，用于设置本地地址 |
| `route_ip` | string | 否 | `""` | PLC 的 IP 地址，用于自动添加 ADS 路由 |
| `timeout` | int | 否 | 5000 | 单次 ADS 操作超时（毫秒） |
| `reconnect_enabled` | bool | 否 | true | 断线后是否自动重连 |
| `reconnect_interval` | float | 否 | 1.0 | 重连初始等待时间（秒） |
| `reconnect_max_interval` | float | 否 | 30.0 | 重连最大等待时间（秒） |
| `reconnect_backoff` | float | 否 | 2.0 | 退避倍数，每次重连失败后等待时间翻倍 |

#### `heartbeat` — 心跳检测

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `interval` | int | 5 | 心跳检测间隔（秒） |
| `max_failures` | int | 3 | 连续失败次数上限，超过后标记为断线并触发重连 |

#### `modbus_slave` — Modbus TCP 从站

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `host` | string | 是 | — | 监听 IP 地址，容器内固定使用 `0.0.0.0` |
| `port` | int | 否 | 502 | Modbus TCP 端口号 |
| `slave_id` | int | 否 | 1 | Modbus 从站 ID |
| `max_connections` | int | 否 | 10 | 最大并发 Modbus 客户端连接数 |

#### `mappings` — 变量映射表

每个映射项的字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ads_var` | string | 是 | ADS 变量名，PLC 中的完整变量路径 |
| `modbus_type` | string | 是 | Modbus 寄存器类型，可选值：`coils`、`discrete_inputs`、`holding_registers`、`input_registers` |
| `modbus_address` | int | 是 | Modbus 起始地址（从 1 开始） |
| `data_type` | string | 是 | 数据类型，可选值见下表 |
| `description` | string | 否 | 变量描述 |

**支持的数据类型：**

| data_type | ADS PLC 类型 | Modbus 寄存器数 | 说明 |
|-----------|-------------|----------------|------|
| `bool` | PLCTYPE_BOOL | 1 (coil) | 布尔值 |
| `int8` | PLCTYPE_SINT | 1 (register) | 有符号 8 位整数 |
| `uint8` | PLCTYPE_USINT | 1 (register) | 无符号 8 位整数 |
| `int16` | PLCTYPE_INT | 1 (register) | 有符号 16 位整数 |
| `uint16` | PLCTYPE_UINT | 1 (register) | 无符号 16 位整数 |
| `int32` | PLCTYPE_DINT | 2 (registers) | 有符号 32 位整数，占用 2 个连续寄存器 |
| `uint32` | PLCTYPE_UDINT | 2 (registers) | 无符号 32 位整数，占用 2 个连续寄存器 |
| `float` | PLCTYPE_REAL | 2 (registers) | 单精度浮点数，占用 2 个连续寄存器 |
| `string` | PLCTYPE_STRING | 1 (register) | 字符串 |

**地址分配注意事项：**
- `int32`、`uint32`、`float` 类型各占用 2 个连续寄存器，分配地址时需预留空间。
- 例如：地址 1 为 `uint16`，地址 2 为 `int32`，则地址 2 和 3 都会被占用，下一个可用地址为 4。
- `coils` 和 `holding_registers` 的地址空间是独立的，可以重复使用。

## Docker Compose 部署

### 目录结构

```
project-root/
├── config/
│   └── mapping.yaml          # 配置文件（宿主机编辑，容器内只读挂载）
├── logs/                      # 日志输出目录（自动创建）
├── docker-compose.yml
├── Dockerfile
├── main.py
├── src/
└── requirements.txt
```

### 部署步骤

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动服务（后台运行）
docker-compose up -d

# 3. 查看实时日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

### docker-compose.yml 说明

```yaml
services:
  ads-gateway:
    build: .
    container_name: ads-modbus-gateway
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./config:/app/config:ro    # 配置文件只读挂载
      - ./logs:/app/logs            # 日志目录挂载
    environment:
      - TZ=Asia/Shanghai
```

关键配置：
- **`network_mode: host`** — 容器直接使用宿主机网络，Modbus 端口对外可见，无需端口映射。
- **`./config:/app/config:ro`** — 配置文件以只读方式挂载，修改配置需在宿主机编辑后重启容器。
- **`restart: unless-stopped`** — 容器异常退出或宿主机重启后自动恢复。

## 服务启动注意事项

### 1. ADS 端口依赖

- 服务启动时 **不要求** ADS 立即连接成功，Modbus 服务会先启动，ADS 连接在后台持续重试。
- 确保 PLC 已开启 ADS 端口（默认 48898），且容器宿主机到 PLC 网络可达。
- 如使用路由模式（配置了 `route_ip`），确保宿主机已安装 TwinCAT ADS Router 或 `pyads` 能自动添加路由。

### 2. 端口冲突

- 容器使用 `network_mode: host`，Modbus 端口（默认 5020）直接绑定宿主机，不能被其他服务占用。
- 检查端口是否可用：`ss -tlnp | grep 5020`

### 3. 防火墙配置

```bash
# 开放 Modbus 端口
sudo firewall-cmd --permanent --add-port=5020/tcp
sudo firewall-cmd --reload

# 或使用 iptables
sudo iptables -A INPUT -p tcp --dport 5020 -j ACCEPT
```

### 4. 日志目录

日志通过 volume 挂载到宿主机 `./logs` 目录，确保该目录存在且有写入权限：

```bash
mkdir -p ./logs
```

### 5. 优雅关闭

`docker-compose down` 发送 `SIGTERM` 信号，服务会依次停止数据同步、Modbus 服务器和 ADS 连接。

### 6. 数据同步机制

- 默认每 0.5 秒从 ADS 读取一次所有映射变量并同步到 Modbus（ADS → Modbus）。
- Modbus 客户端写入的数据会实时回写到 ADS（Modbus → ADS）。
- 当 Modbus 侧写入了一个值，该变量在下一次 ADS→Modbus 同步周期中会被跳过，避免覆盖。

### 7. 重连策略

- ADS 连接断开后，使用指数退避策略自动重连，初始间隔 1 秒，最大 30 秒。
- 心跳检测每 5 秒一次，连续 3 次失败后触发重连。
- 重连过程中 Modbus 服务不受影响，外部客户端仍可读取上次同步的值。

### 8. Modbus 写操作限制

- `coils` 类型支持写入（功能码 5/15）
- `holding_registers` 类型支持写入（功能码 6/16）
- `discrete_inputs` 和 `input_registers` 为只读，不支持写入

## 故障排查

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| 日志报 "ADS connection failed" | PLC 不可达或端口未开放 | 检查宿主机到 PLC 的网络连通性，确认 ADS 端口已开启 |
| Modbus 客户端读到全 0 | ADS 未连接或变量名错误 | 查看日志确认 ADS 连接状态，验证 `ads_var` 名称 |
| 容器反复重启 | 配置文件错误或端口被占用 | `docker-compose logs` 查看错误，`ss -tlnp | grep 5020` 检查端口 |
| 日志报 "Config validation failed" | 配置文件格式错误 | 检查 `config/mapping.yaml` 的 YAML 语法和必填字段 |
| 数据更新不及时 | `sync_interval` 设置过大 | 减小 `sync_interval` 值（单位：秒） |

### 查看日志

```bash
# 实时日志
docker-compose logs -f --tail=100

# 或直接查看宿主机日志文件
tail -f ./logs/gateway.log
```
