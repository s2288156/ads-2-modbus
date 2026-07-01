# ADS to Modbus Gateway — Deployment Guide

## Overview

This project is an ADS (Automation Device Specification) to Modbus TCP gateway service. It synchronizes ADS variables from Beckhoff/TwinCAT PLCs to Modbus registers in real time, supporting bidirectional data flow.

## Prerequisites

- Docker and Docker Compose
- Beckhoff PLC running TwinCAT 3 with ADS port open (default: 48898)

## Configuration

The configuration file is located at `config/mapping.yaml`. It is mounted read-only into the container via Docker Compose.

### Full Configuration Structure

```yaml
# ADS connection settings
ads_connection:
  ams_net_id: "127.0.0.1.1.1"   # PLC AMS Net ID (required)
  port: 48898                    # ADS port (default: 48898)
  local_ams_net_id: ""           # Local AMS Net ID (optional)
  route_ip: ""                   # PLC IP address (optional, for route setup)
  timeout: 5000                  # ADS operation timeout in ms
  reconnect_enabled: true        # Auto-reconnect on disconnect
  reconnect_interval: 1.0        # Initial reconnect interval (seconds)
  reconnect_max_interval: 30.0   # Max reconnect interval (seconds)
  reconnect_backoff: 2.0         # Backoff multiplier

# Heartbeat settings
heartbeat:
  interval: 5                    # Heartbeat check interval (seconds)
  max_failures: 3                # Max consecutive failures before reconnect

# Modbus slave settings
modbus_slave:
  host: "0.0.0.0"               # Listen address (always 0.0.0.0 inside container)
  port: 5020                     # Modbus TCP port
  slave_id: 1                    # Modbus slave ID
  max_connections: 10            # Max concurrent connections

# Data sync interval (seconds)
sync_interval: 0.5

# Logging settings
logging:
  log_dir: "/app/logs"           # Log directory (container path, mounted to host via volume)
  log_file: "gateway.log"        # Log filename
  level: "INFO"                  # Log level (DEBUG/INFO/WARNING/ERROR)
  max_bytes: 209715200           # Max single log file size (200MB)
  max_days: 7                    # Log retention days
  max_total_bytes: 2147483648    # Total log size limit (2GB)
  backup_count: 7                # Log backup count
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Variable mappings
mappings:
  - ads_var: "Proces.BoxReady_AM68"     # ADS variable name (full path in PLC)
    modbus_type: "coils"                 # Modbus register type
    modbus_address: 1                    # Modbus start address (1-based)
    data_type: "bool"                    # Data type
    description: "BoxReady AM68"         # Description (optional)
```

### Field Reference

#### `ads_connection` — ADS Connection Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ams_net_id` | string | yes | — | PLC AMS Net ID, format: `x.x.x.x.x.x` (6 dot-separated numeric segments) |
| `port` | int | no | 48898 | ADS communication port |
| `local_ams_net_id` | string | no | `""` | Local AMS Net ID for setting local address |
| `route_ip` | string | no | `""` | PLC IP address for automatic ADS route setup |
| `timeout` | int | no | 5000 | Single ADS operation timeout (ms) |
| `reconnect_enabled` | bool | no | true | Enable auto-reconnect on disconnect |
| `reconnect_interval` | float | no | 1.0 | Initial reconnect wait time (seconds) |
| `reconnect_max_interval` | float | no | 30.0 | Maximum reconnect wait time (seconds) |
| `reconnect_backoff` | float | no | 2.0 | Backoff multiplier (wait time doubles on each failure) |

#### `heartbeat` — Heartbeat Detection

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `interval` | int | 5 | Heartbeat check interval (seconds) |
| `max_failures` | int | 3 | Max consecutive failures before marking disconnected and triggering reconnect |

#### `modbus_slave` — Modbus TCP Slave

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `host` | string | yes | — | Listen IP address, always `0.0.0.0` inside container |
| `port` | int | no | 502 | Modbus TCP port |
| `slave_id` | int | no | 1 | Modbus slave ID |
| `max_connections` | int | no | 10 | Max concurrent Modbus client connections |

#### `mappings` — Variable Mapping Table

Each mapping entry:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ads_var` | string | yes | ADS variable name (full path in PLC) |
| `modbus_type` | string | yes | Modbus register type: `coils`, `discrete_inputs`, `holding_registers`, `input_registers` |
| `modbus_address` | int | yes | Modbus start address (1-based) |
| `data_type` | string | yes | Data type (see table below) |
| `description` | string | no | Variable description |

**Supported Data Types:**

| data_type | ADS PLC Type | Modbus Registers | Description |
|-----------|-------------|------------------|-------------|
| `bool` | PLCTYPE_BOOL | 1 (coil) | Boolean |
| `int8` | PLCTYPE_SINT | 1 (register) | Signed 8-bit integer |
| `uint8` | PLCTYPE_USINT | 1 (register) | Unsigned 8-bit integer |
| `int16` | PLCTYPE_INT | 1 (register) | Signed 16-bit integer |
| `uint16` | PLCTYPE_UINT | 1 (register) | Unsigned 16-bit integer |
| `int32` | PLCTYPE_DINT | 2 (registers) | Signed 32-bit integer, occupies 2 consecutive registers |
| `uint32` | PLCTYPE_UDINT | 2 (registers) | Unsigned 32-bit integer, occupies 2 consecutive registers |
| `float` | PLCTYPE_REAL | 2 (registers) | Single-precision float, occupies 2 consecutive registers |
| `string` | PLCTYPE_STRING | 1 (register) | String |

**Address Allocation Notes:**
- `int32`, `uint32`, and `float` types each occupy 2 consecutive registers — leave room when assigning addresses.
- Example: address 1 is `uint16`, address 2 is `int32` — both address 2 and 3 are consumed; next available address is 4.
- `coils` and `holding_registers` have independent address spaces and can reuse the same numbers.

## Docker Compose Deployment

### Directory Layout

```
project-root/
├── config/
│   └── mapping.yaml          # Config file (edited on host, mounted read-only)
├── logs/                      # Log output directory (auto-created)
├── docker-compose.yml
├── Dockerfile
├── main.py
├── src/
└── requirements.txt
```

### Deployment Steps

```bash
# 1. Build image
docker-compose build

# 2. Start service (detached)
docker-compose up -d

# 3. View live logs
docker-compose logs -f

# 4. Stop service
docker-compose down
```

### docker-compose.yml Overview

```yaml
services:
  ads-gateway:
    build: .
    container_name: ads-modbus-gateway
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./config:/app/config:ro    # Config file mounted read-only
      - ./logs:/app/logs            # Log directory mounted
    environment:
      - TZ=Asia/Shanghai
```

Key settings:
- **`network_mode: host`** — Container shares the host's network stack. Modbus port is directly accessible without port mapping.
- **`./config:/app/config:ro`** — Config file is mounted read-only. To change config, edit on the host and restart the container.
- **`restart: unless-stopped`** — Container auto-restarts on crash or host reboot.

## Startup Notes

### 1. ADS Port Dependency

- The service does **not** require an immediate ADS connection at startup. The Modbus server starts first; ADS connects and retries in the background.
- Ensure the PLC has its ADS port open (default 48898) and the host machine can reach it over the network.
- If using route mode (`route_ip` configured), ensure TwinCAT ADS Router is installed on the host or `pyads` can add the route automatically.

### 2. Port Conflicts

- With `network_mode: host`, the Modbus port (default 5020) binds directly to the host and must not be occupied by other services.
- Check availability: `ss -tlnp | grep 5020`

### 3. Firewall Configuration

```bash
# Open Modbus port
sudo firewall-cmd --permanent --add-port=5020/tcp
sudo firewall-cmd --reload

# Or with iptables
sudo iptables -A INPUT -p tcp --dport 5020 -j ACCEPT
```

### 4. Log Directory

Logs are mounted to the host's `./logs` directory. Ensure it exists and is writable:

```bash
mkdir -p ./logs
```

### 5. Graceful Shutdown

`docker-compose down` sends `SIGTERM` to the container. The service stops data sync, Modbus server, and ADS connection in sequence.

### 6. Data Synchronization

- By default, all mapped variables are read from ADS and synced to Modbus every 0.5 seconds (ADS -> Modbus).
- Values written by Modbus clients are immediately written back to ADS (Modbus -> ADS).
- When Modbus-side writes a value, that variable is skipped in the next ADS->Modbus sync cycle to avoid overwriting.

### 7. Reconnection Strategy

- ADS uses exponential backoff for reconnection: initial interval 1s, max 30s.
- Heartbeat runs every 5 seconds; 3 consecutive failures trigger reconnection.
- During reconnection, the Modbus service continues running — external clients can still read the last synchronized values.

### 8. Modbus Write Restrictions

- `coils` — writable (function codes 5/15)
- `holding_registers` — writable (function codes 6/16)
- `discrete_inputs` and `input_registers` — read-only, writes are not supported

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| "ADS connection failed" in logs | PLC unreachable or port not open | Check network from host to PLC, verify ADS port is open |
| Modbus clients read all zeros | ADS not connected or wrong variable name | Check logs for ADS connection status, verify `ads_var` names |
| Container keeps restarting | Config error or port in use | `docker-compose logs` for errors, `ss -tlnp | grep 5020` for port |
| "Config validation failed" in logs | Invalid YAML or missing required fields | Validate `config/mapping.yaml` syntax and required fields |
| Data updates are slow | `sync_interval` too large | Reduce `sync_interval` value (unit: seconds) |

### Viewing Logs

```bash
# Live logs
docker-compose logs -f --tail=100

# Or view the log file on the host directly
tail -f ./logs/gateway.log
```
