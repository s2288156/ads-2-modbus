import threading
import time
import logging
from pyads.testserver import AdsTestServer
from pyads.testserver.advanced_handler import AdvancedHandler, PLCVariable
from pyads import constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟场景配置:
# - 服务器绑定在 127.0.0.1 (真实可达)
# - ams_net_id 配置为 999.999.999.999.1.1 (虚构，不可达)
# - route_ip 配置为 127.0.0.1 (真实可达)
# 这样可以测试当 ams_net_id 不通时，是否能通过 route_ip 回退连接

FAKE_AMS_NET_ID = "127.0.0.1.1.1"  # 虚构的不可达 AMS Net ID
REAL_BIND_IP = "127.0.0.1"               # 服务器实际绑定 IP
SERVER_PORT = 48898


class ADSHandler(AdvancedHandler):
    def __init__(self):
        super().__init__()
        self._register_variables()

    def _get_var_name(self, index_group, index_offset):
        """根据 index_group/index_offset 查找变量名"""
        var = self._data.get((index_group, index_offset))
        return var.name if var else f"UNKNOWN(0x{index_group:X},0x{index_offset:X})"

    def handle_request(self, request):
        """覆写 handle_request，在 READ/WRITE 时额外打印变量名"""
        import struct
        from pyads.testserver.testserver import AmsResponseData

        command_id = struct.unpack("<H", request.ams_header.command_id)[0]

        if command_id == constants.ADSCOMMAND_READ:
            data = request.ams_header.data
            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            var_name = self._get_var_name(index_group, index_offset)
            logger.info(f"[READ] {var_name} (0x{index_group:X}:0x{index_offset:X})")

        elif command_id == constants.ADSCOMMAND_WRITE:
            data = request.ams_header.data
            index_group = struct.unpack("<I", data[:4])[0]
            index_offset = struct.unpack("<I", data[4:8])[0]
            plc_datatype = struct.unpack("<I", data[8:12])[0]
            value = data[12:(12 + plc_datatype)]
            var_name = self._get_var_name(index_group, index_offset)
            logger.info(f"[WRITE] {var_name} (0x{index_group:X}:0x{index_offset:X}) = {value.hex()}")

        try:
            return super().handle_request(request)
        except KeyError as e:
            state = struct.unpack("<H", request.ams_header.state_flags)[0]
            state = struct.pack("<H", state | 0x0001)
            error_code = struct.pack("<I", 0x0702)  # ADS错误: 变量不存在
            logger.warning(f"[ERROR] Variable not found: {e}")
            return AmsResponseData(state, error_code, b"")

    def _register_variables(self):
        variables = [
            PLCVariable( name='Proces.BoxReady_AM46',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=6),
            PLCVariable( name='Proces.BoxReady_AM71',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=2),
            PLCVariable( name='Proces.PG_Full_Ready_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=17),
            PLCVariable( name='Proces.BoxReady_AM46_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=7),
            PLCVariable( name='Proces.PG_Box_Ready_cb', value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=15),
            PLCVariable( name='Proces.PG_Full_Ready',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=16),
            PLCVariable( name='Proces.BoxReady_AM72',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=4),
            PLCVariable( name='Proces.BoxReady_AM56',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=8),
            PLCVariable( name='Proces.BoxReady_AM58_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=11),
            PLCVariable( name='Proces.BoxReady_AM68_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=1),
            PLCVariable( name='Proces.BoxReady_AM59',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=12),
            PLCVariable( name='Proces.BoxReady_AM68',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=0),
            PLCVariable( name='Proces.BoxReady_AM72_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=5),
            PLCVariable( name='Proces.BoxReady_AM71_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=3),
            PLCVariable( name='Proces.BoxReady_AM58',   value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=10),
            PLCVariable( name='Proces.BoxReady_AM59_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=13),
            PLCVariable( name='Proces.PG_Full_End_cb',  value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=18),
            PLCVariable( name='Proces.BoxReady_AM56_cb',value=False,ads_type=constants.ADST_BIT,symbol_type='BOOL',index_group=0x4020,index_offset=9),

            PLCVariable( name='B.robWarningCode_R1',    value=1,ads_type=constants.ADST_UINT16,symbol_type='UINT',index_group=0x4020,index_offset=204),
            PLCVariable( name='B.batteryLevel_R1',      value=1,ads_type=constants.ADST_UINT8,symbol_type='USINT',index_group=0x4020,index_offset=200),

            PLCVariable( name='C.robWarningCode_R2',    value=1,ads_type=constants.ADST_UINT16,symbol_type='UINT',index_group=0x4020,index_offset=404),
            PLCVariable( name='C.batteryLevel_R2',      value=1,ads_type=constants.ADST_UINT8,symbol_type='USINT',index_group=0x4020,index_offset=400),

        ]

        for var in variables:
            self.add_variable(var)
            logger.info(f"Registered variable: {var.name} -> index_group=0x{var.index_group:08X}, index_offset=0x{var.index_offset:08X}, type={var.symbol_type}, value={var.value}")


def _patch_logging():
    """Monkey-patch AdsTestServer/AdsClientConnection 添加连接断开日志"""
    from pyads.testserver.testserver import AdsClientConnection as _OrigClient

    _orig_run = _OrigClient.run

    def _patched_run(self):
        addr = self.client_address
        logger.info(f"[CONNECTED] Client {addr[0]}:{addr[1]}")
        try:
            _orig_run(self)
        finally:
            logger.info(f"[DISCONNECTED] Client {addr[0]}:{addr[1]}")

    _OrigClient.run = _patched_run


def start_ads_test_server(bind_ip=REAL_BIND_IP, port=SERVER_PORT):
    _patch_logging()
    handler = ADSHandler()
    server = AdsTestServer(handler, bind_ip, port)
    logger.info(f"Starting ADS Test Server on {bind_ip}:{port}...")
    server.start()
    return server


def print_test_config():
    print("=" * 60)
    print("Test Scenario: ams_net_id unreachable, fallback to route_ip")
    print("=" * 60)
    print(f"Server binds to:               {REAL_BIND_IP}:{SERVER_PORT}")
    print(f"Fake AMS Net ID (unreachable): {FAKE_AMS_NET_ID}")
    print(f"Real route_ip:                 {REAL_BIND_IP}")
    print()
    print("Client config (mapping.yaml):")
    print(f"  ams_net_id:            \"{FAKE_AMS_NET_ID}\"")
    print(f"  port:                  {SERVER_PORT}")
    print(f"  route_ip:              \"{REAL_BIND_IP}\"")
    print(f"  fallback_to_route_ip:  true")
    print("=" * 60)


if __name__ == "__main__":
    print_test_config()
    server = start_ads_test_server()
    logger.info("ADS Test Server is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping ADS Test Server...")
        server.stop()
