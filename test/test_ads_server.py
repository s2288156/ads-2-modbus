import threading
import time
import pyads
from pyads.testserver import AdsTestServer, BasicHandler

class TestHandler(BasicHandler):
    def __init__(self):
        super().__init__()
        self.variables = {
            'GVL.int_value': 1234,
            'GVL.float_value': 3.14,
            'GVL.bool_value': True,
            'GVL.int16_value': 5678,
            'GVL.int32_value': 123456789
        }
    
    def read_by_name(self, name):
        if name in self.variables:
            return self.variables[name]
        raise Exception(f"Variable {name} not found")
    
    def write_by_name(self, name, value):
        if name in self.variables:
            self.variables[name] = value
            print(f"ADS Server: Variable {name} set to {value}")
            return True
        raise Exception(f"Variable {name} not found")

def start_ads_test_server():
    handler = TestHandler()
    server = AdsTestServer(handler, '127.0.0.1.1.1', 851)
    print("Starting ADS Test Server on 127.0.0.1.1.1:851...")
    server.start()
    return server

if __name__ == "__main__":
    server = start_ads_test_server()
    print("ADS Test Server is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ADS Test Server...")
        server.stop()