# ADS to Modbus Gateway — Deployment Guide

## Overview

ADS (Automation Device Specification) to Modbus TCP gateway service. Synchronizes ADS variables from Beckhoff/TwinCAT PLCs to Modbus registers in real time, with bidirectional data flow.

## Prerequisites

- Docker and Docker Compose
- Beckhoff PLC running TwinCAT 3 with ADS port open (default: 48898)

## Configuration

Config file at `config/mapping.yaml`, mounted read-only into the container.

```yaml
ads_connection:
  ams_net_id: "127.0.0.1.1.1"   # PLC AMS Net ID (required)
  port: 48898                    # ADS port (default: 48898)
  local_ams_net_id: ""           # Local AMS Net ID (optional)
  route_ip: ""                   # PLC IP for route setup (optional)
  timeout: 5000                  # ADS operation timeout (ms)
  reconnect_enabled: true        # Auto-reconnect on disconnect
  reconnect_interval: 1.0        # Initial reconnect interval (seconds)
  reconnect_max_interval: 30.0   # Max reconnect interval (seconds)
  reconnect_backoff: 2.0         # Backoff multiplier

heartbeat:
  interval: 5                    # Heartbeat check interval (seconds)
  max_failures: 3                # Max failures before reconnect

modbus_slave:
  host: "0.0.0.0"               # Listen address (always 0.0.0.0 in container)
  port: 5020                     # Modbus TCP port
  slave_id: 1                    # Modbus slave ID
  max_connections: 10            # Max concurrent connections

sync_interval: 0.5               # Data sync interval (seconds)

logging:
  log_dir: "/app/logs"
  log_file: "gateway.log"
  level: "INFO"                  # DEBUG/INFO/WARNING/ERROR
  max_bytes: 209715200           # Max single log file (200MB)
  max_days: 7
  max_total_bytes: 2147483648    # Total log size limit (2GB)
  backup_count: 7

mappings:
  - ads_var: "Proces.BoxReady_AM68"     # ADS variable name (full PLC path)
    modbus_type: "coils"                 # Modbus register type
    modbus_address: 1                    # Modbus start address (1-based)
    data_type: "bool"                    # Data type
    description: "BoxReady AM68"         # Description (optional)
```

### `ads_connection` Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ams_net_id` | string | — | PLC AMS Net ID, format `x.x.x.x.x.x` (required) |
| `port` | int | 48898 | ADS communication port |
| `local_ams_net_id` | string | `""` | Local AMS Net ID |
| `route_ip` | string | `""` | PLC IP for automatic ADS route setup |
| `timeout` | int | 5000 | Single ADS operation timeout (ms) |
| `reconnect_enabled` | bool | true | Auto-reconnect on disconnect |
| `reconnect_interval` | float | 1.0 | Initial reconnect wait (seconds) |
| `reconnect_max_interval` | float | 30.0 | Maximum reconnect wait (seconds) |
| `reconnect_backoff` | float | 2.0 | Backoff multiplier |

### `modbus_slave` Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | string | — | Listen IP, always `0.0.0.0` in container (required) |
| `port` | int | 502 | Modbus TCP port |
| `slave_id` | int | 1 | Modbus slave ID |
| `max_connections` | int | 10 | Max concurrent connections |

### `mappings` Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ads_var` | string | yes | ADS variable name (full PLC path) |
| `modbus_type` | string | yes | `coils` / `discrete_inputs` / `holding_registers` / `input_registers` |
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
| `int32` | PLCTYPE_DINT | 2 (registers) | Signed 32-bit integer, 2 consecutive registers |
| `uint32` | PLCTYPE_UDINT | 2 (registers) | Unsigned 32-bit integer, 2 consecutive registers |
| `float` | PLCTYPE_REAL | 2 (registers) | Single-precision float, 2 consecutive registers |
| `string` | PLCTYPE_STRING | 1 (register) | String |

> `int32`/`uint32`/`float` each occupy 2 consecutive registers — leave room when assigning addresses. `coils` and `holding_registers` have independent address spaces.

## Deployment

### Directory Layout

```
project-root/
├── config/
│   └── mapping.yaml
├── logs/
├── docker-compose.yml
├── Dockerfile
├── main.py
├── src/
└── requirements.txt
```

### Deployment Steps

```bash
# Build image (with version tag)
TAG=1.0.1 docker compose build

# Start service (detached)
docker compose up -d

# View live logs
docker compose logs -f

# Stop service
docker compose down
```

### docker-compose.yml

```yaml
services:
  ads-gateway:
    build: .
    image: ads-modbus-gateway:${TAG:-latest}
    container_name: ads-modbus-gateway
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    environment:
      - TZ=Asia/Shanghai
```

Key settings:
- **`network_mode: host`** — Container shares the host's network stack. Modbus port is directly accessible without port mapping.
- **`./config:/app/config:ro`** — Config file mounted read-only. Edit on host and restart container to apply changes.
- **`restart: unless-stopped`** — Auto-restarts on crash or host reboot.

## Notes

1. **ADS Connection**: Service starts without requiring immediate ADS connection. Modbus starts first; ADS connects and retries in background. Ensure PLC ADS port is reachable.
2. **Port Conflicts**: With host networking, Modbus port (default 5020) binds directly to host. Check availability: `ss -tlnp | grep 5020`
3. **Firewall**: Open Modbus port, e.g. `sudo firewall-cmd --permanent --add-port=5020/tcp && sudo firewall-cmd --reload`
4. **Log Directory**: Ensure `./logs` exists and is writable: `mkdir -p ./logs`
5. **Graceful Shutdown**: `docker-compose down` sends SIGTERM; service stops data sync, Modbus server, and ADS connection in sequence.
6. **Data Sync**: Default 0.5s interval, reads from ADS and syncs to Modbus (ADS→Modbus). Modbus writes are immediately sent back to ADS (Modbus→ADS); that variable is skipped in the next sync cycle.
7. **Reconnection**: Exponential backoff (initial 1s, max 30s). Heartbeat every 5s; 3 consecutive failures trigger reconnect. Modbus service remains available during reconnection.
8. **Write Access**: `coils` and `holding_registers` support writes. `discrete_inputs` and `input_registers` are read-only.

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| "ADS connection failed" in logs | PLC unreachable or port not open | Check network, verify ADS port is open |
| Modbus clients read all zeros | ADS not connected or wrong variable name | Check logs for ADS status, verify `ads_var` names |
| Container keeps restarting | Config error or port in use | `docker compose logs` for errors |
| "Config validation failed" in logs | Invalid YAML or missing required fields | Validate `config/mapping.yaml` |
| Data updates are slow | `sync_interval` too large | Reduce `sync_interval` value |

```bash
# Live logs
docker compose logs -f --tail=100

# Or view log file directly on host
tail -f ./logs/gateway.log
```
