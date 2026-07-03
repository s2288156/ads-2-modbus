import asyncio
import logging
import pyads

logger = logging.getLogger(__name__)

# plc_datatype 映射
PLCDATATYPE_MAP = {
    'bool': pyads.PLCTYPE_BOOL,
    'int8': pyads.PLCTYPE_SINT,
    'uint8': pyads.PLCTYPE_USINT,
    'int16': pyads.PLCTYPE_INT,
    'uint16': pyads.PLCTYPE_UINT,
    'int32': pyads.PLCTYPE_DINT,
    'uint32': pyads.PLCTYPE_UDINT,
    'float': pyads.PLCTYPE_REAL,
    'string': pyads.PLCTYPE_STRING,
}


class ADSClient:
    def __init__(self, ams_net_id, port, local_ams_net_id=None, route_ip=None,
                 timeout=5000, reconnect_enabled=True, reconnect_interval=1.0,
                 reconnect_max_interval=30.0, reconnect_backoff=2.0,
                 heartbeat_interval=5.0, heartbeat_max_failures=3,
                 fallback_to_route_ip=True):
        self.ams_net_id = ams_net_id
        self.port = port
        self.local_ams_net_id = local_ams_net_id
        self.route_ip = route_ip
        self.timeout = timeout
        self.connection = None
        self._connected = False
        self._fallback_to_route_ip = fallback_to_route_ip

        self._reconnect_enabled = reconnect_enabled
        self._reconnect_interval = reconnect_interval
        self._reconnect_max = reconnect_max_interval
        self._reconnect_backoff = reconnect_backoff
        self._lock = asyncio.Lock()

        # 心跳相关
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_max_failures = heartbeat_max_failures
        self._heartbeat_failures = 0
        self._heartbeat_task = None

    @property
    def connected(self):
        return self._connected

    def connect(self):
        """同步连接，用于启动时调用。"""
        self._setup_route()
        self._open_connection()

    def _setup_route(self):
        if self.local_ams_net_id:
            pyads.open_port()
            pyads.set_local_address(self.local_ams_net_id)
            logger.info(f"Set local AMS Net ID: {self.local_ams_net_id}")

        if self.route_ip:
            try:
                pyads.add_route(self.ams_net_id, self.route_ip)
                logger.info(f"ADS route added: {self.ams_net_id} -> {self.route_ip}")
            except Exception as e:
                if "already exists" in str(e):
                    logger.debug(f"ADS route already exists: {self.ams_net_id}")
                else:
                    logger.warning(f"Failed to add route: {e}")
                    # 不再直接 raise，允许后续尝试直连

    def _open_connection(self):
        try:
            # 尝试使用配置的 ams_net_id 连接
            self.connection = pyads.Connection(self.ams_net_id, self.port)
            self.connection.open()
            self._connected = True
            self._heartbeat_failures = 0
            logger.info(f"ADS connected: {self.ams_net_id}:{self.port}")
        except Exception as e:
            logger.warning(f"ADS connection failed with ams_net_id {self.ams_net_id}: {e}")
            
            # 如果配置了 route_ip 且启用了回退，尝试使用 route_ip 直连
            if self.route_ip and self._fallback_to_route_ip:
                logger.info(f"Trying direct connection via route_ip: {self.route_ip}:{self.port}")
                try:
                    # 使用 route_ip 作为远程 IP，尝试直连
                    self.connection = pyads.Connection(self.ams_net_id, self.port, 
                                                       ip_address=self.route_ip)
                    self.connection.open()
                    self._connected = True
                    self._heartbeat_failures = 0
                    logger.info(f"ADS connected via route_ip: {self.route_ip}:{self.port}")
                    return
                except Exception as e2:
                    logger.error(f"ADS connection via route_ip also failed: {e2}")
            
            self._connected = False
            raise

    def disconnect(self):
        self.stop_heartbeat()
        if self.connection:
            try:
                self.connection.close()
                logger.info("ADS connection closed")
            except Exception as e:
                logger.error(f"Error closing ADS connection: {e}")
            finally:
                self._connected = False
                self.connection = None

    # ---- 异步重连 ----

    async def ensure_connected(self):
        if self._connected:
            return
        if not self._reconnect_enabled:
            raise ConnectionError("ADS client not connected and reconnect disabled")
        async with self._lock:
            if self._connected:
                return
            await self._reconnect()

    async def _reconnect(self):
        interval = self._reconnect_interval
        while True:
            try:
                route_info = f" via {self.route_ip}" if self.route_ip else ""
                logger.info(f"ADS reconnecting to {self.ams_net_id}:{self.port}{route_info}...")
                self._open_connection()
                logger.info("ADS reconnected successfully")
                return
            except Exception as e:
                logger.warning(f"ADS reconnect failed: {e}, retry in {interval:.1f}s")
                await asyncio.sleep(interval)
                interval = min(interval * self._reconnect_backoff, self._reconnect_max)

    # ---- 心跳 ----

    def start_heartbeat(self, interval=None, max_failures=None):
        if interval is not None:
            self._heartbeat_interval = interval
        if max_failures is not None:
            self._heartbeat_max_failures = max_failures
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def stop_heartbeat(self):
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            try:
                if not self._connected or not self.connection:
                    continue
                # 使用 read_device_info 作为轻量级心跳
                self.connection.read_device_info()
                self._heartbeat_failures = 0
                logger.debug("ADS heartbeat OK")
            except Exception as e:
                self._heartbeat_failures += 1
                logger.warning(f"ADS heartbeat failed ({self._heartbeat_failures}/{self._heartbeat_max_failures}): {e}")
                if self._heartbeat_failures >= self._heartbeat_max_failures:
                    logger.error("ADS heartbeat lost, triggering reconnect")
                    self._connected = False
                    self._heartbeat_failures = 0

    # ---- 读写操作 ----

    def read_by_name(self, var_name, plc_datatype=None):
        if not self._connected:
            raise ConnectionError("ADS client not connected")

        try:
            value = self.connection.read_by_name(var_name, plc_datatype)
            logger.debug(f"Read ADS variable {var_name} = {value}")
            return value
        except pyads.ADSError as e:
            logger.error(f"ADS error reading {var_name}: {e}")
            self._handle_ads_error(e)
            raise
        except Exception as e:
            logger.error(f"Failed to read ADS variable {var_name}: {e}")
            self._connected = False
            raise

    def write_by_name(self, var_name, value, plc_datatype=None):
        if not self._connected:
            raise ConnectionError("ADS client not connected")

        try:
            self.connection.write_by_name(var_name, value, plc_datatype)
            logger.debug(f"Wrote ADS variable {var_name} = {value}")
        except pyads.ADSError as e:
            logger.error(f"ADS error writing {var_name}: {e}")
            self._handle_ads_error(e)
            raise
        except Exception as e:
            logger.error(f"Failed to write ADS variable {var_name}: {e}")
            self._connected = False
            raise

    def read_list_by_name(self, var_names):
        if not self._connected:
            raise ConnectionError("ADS client not connected")
        try:
            values = self.connection.read_list_by_name(var_names)
            logger.debug(f"Batch read {len(var_names)} ADS variables")
            return values
        except pyads.ADSError as e:
            logger.error(f"ADS batch read error: {e}")
            self._handle_ads_error(e)
            raise
        except Exception as e:
            logger.error(f"Failed batch read: {e}")
            self._connected = False
            raise

    def write_list_by_name(self, values_dict):
        if not self._connected:
            raise ConnectionError("ADS client not connected")
        try:
            self.connection.write_list_by_name(values_dict)
            logger.debug(f"Batch write {len(values_dict)} ADS variables")
        except pyads.ADSError as e:
            logger.error(f"ADS batch write error: {e}")
            self._handle_ads_error(e)
            raise
        except Exception as e:
            logger.error(f"Failed batch write: {e}")
            self._connected = False
            raise

    def _handle_ads_error(self, e):
        error_code = getattr(e, 'error_code', None)
        if error_code == 0x07:  # ADS error: timeout
            logger.warning("ADS timeout detected")
        elif error_code == 0x0E:  # Symbol not found
            logger.error("ADS variable not found in PLC")
        elif error_code in (0x01, 0x02, 0x03):  # general / target not found / port not found
            logger.error(f"ADS connection error (code=0x{error_code:02X}), marking disconnected")
            self._connected = False

    @staticmethod
    def get_plc_datatype(data_type_str):
        return PLCDATATYPE_MAP.get(data_type_str)
