import logging
import pyads

logger = logging.getLogger(__name__)

class ADSClient:
    def __init__(self, ams_net_id, port):
        self.ams_net_id = ams_net_id
        self.port = port
        self.connection = None
        self.connected = False
    
    def connect(self):
        try:
            self.connection = pyads.Connection(self.ams_net_id, self.port)
            self.connection.open()
            self.connected = True
            logger.info(f"ADS connected: {self.ams_net_id}:{self.port}")
        except Exception as e:
            self.connected = False
            logger.error(f"ADS connection failed: {e}")
            raise
    
    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
                self.connected = False
                logger.info("ADS connection closed")
            except Exception as e:
                logger.error(f"Error closing ADS connection: {e}")
    
    def read_by_name(self, var_name, plc_datatype=None):
        if not self.connected:
            raise ConnectionError("ADS client not connected")
        
        try:
            value = self.connection.read_by_name(var_name, plc_datatype)
            logger.debug(f"Read ADS variable {var_name} = {value}")
            return value
        except Exception as e:
            logger.error(f"Failed to read ADS variable {var_name}: {e}")
            raise
    
    def write_by_name(self, var_name, value, plc_datatype=None):
        if not self.connected:
            raise ConnectionError("ADS client not connected")
        
        try:
            self.connection.write_by_name(var_name, value, plc_datatype)
            logger.debug(f"Wrote ADS variable {var_name} = {value}")
        except Exception as e:
            logger.error(f"Failed to write ADS variable {var_name}: {e}")
            raise