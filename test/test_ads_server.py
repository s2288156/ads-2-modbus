import threading
import time
import logging
from pyads.testserver import AdsTestServer
from pyads.testserver.advanced_handler import AdvancedHandler, PLCVariable
from pyads import constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ADSHandler(AdvancedHandler):
    def __init__(self):
        super().__init__()
        self._register_variables()
    
    def _register_variables(self):
        variables = [
            PLCVariable(
                name='GVL.bool_value',
                value=True,
                ads_type=constants.ADST_BIT,
                symbol_type='BOOL',
                index_group=0x4020,
                index_offset=0
            ),
            PLCVariable(
                name='GVL.int_value',
                value=1234,
                ads_type=constants.ADST_INT32,
                symbol_type='DINT',
                index_group=0x4020,
                index_offset=16
            ),
            PLCVariable(
                name='GVL.int16_value',
                value=5678,
                ads_type=constants.ADST_INT16,
                symbol_type='INT',
                index_group=0x4020,
                index_offset=20
            ),
            PLCVariable(
                name='GVL.float_value',
                value=3.14,
                ads_type=constants.ADST_REAL32,
                symbol_type='REAL',
                index_group=0x4020,
                index_offset=32
            ),
            PLCVariable(
                name='GVL.uint16_value',
                value=30000,
                ads_type=constants.ADST_UINT16,
                symbol_type='UINT',
                index_group=0x4020,
                index_offset=36
            ),
            PLCVariable(
                name='GVL.usint_value',
                value=255,
                ads_type=constants.ADST_UINT8,
                symbol_type='USINT',
                index_group=0x4020,
                index_offset=38
            ),
            PLCVariable(
                name='GVL.uint32_value',
                value=4294967295,
                ads_type=constants.ADST_UINT32,
                symbol_type='UDINT',
                index_group=0x4020,
                index_offset=40
            ),
        ]
        
        for var in variables:
            self.add_variable(var)
            logger.info(f"Registered variable: {var.name} -> index_group=0x{var.index_group:08X}, index_offset=0x{var.index_offset:08X}, type={var.symbol_type}, value={var.value}")

def start_ads_test_server():
    handler = ADSHandler()
    server = AdsTestServer(handler, '127.0.0.1', 48898)
    logger.info("Starting ADS Test Server on 127.0.0.1:48898...")
    logger.info("AMS Net ID: 127.0.0.1.1.1")
    server.start()
    return server

if __name__ == "__main__":
    server = start_ads_test_server()
    logger.info("ADS Test Server is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping ADS Test Server...")
        server.stop()