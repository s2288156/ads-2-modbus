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