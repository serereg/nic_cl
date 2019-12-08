# for workin with opc
import traceback
from Cooler import Cooler

from pyModbusTCP.client import ModbusClient
import time
from pyModbusTCP import utils

class FloatModbusClient(ModbusClient):
    def read_float(self, address, number=1):
        reg_l = self.read_holding_registers(address, number * 2)
        if reg_l:
            return [utils.decode_ieee(f) for f in utils.word_list_to_long(reg_l)]
        else:
            return None

    def read_float_inp(self, address, number=1):
        reg_l = self.read_input_registers(address, number * 2)
        if reg_l:
            return [utils.decode_ieee(f) for f in utils.word_list_to_long(reg_l)]
        else:
            return None
        
    def write_float(self, address, floats_list):
        b32_l = [utils.encode_ieee(f) for f in floats_list]
        b16_l = utils.long_list_to_word(b32_l)
        return self.write_multiple_registers(address, b16_l)

SERVER_HOST = "localhost"
SERVER_PORT = 502

def run_in_executor(f):
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, f, *args, **kwargs)
    return wrapper

class OPC:
    
    def __init__(self, host, items):
        self.host = host
        self.items = items
        self.coolers_arr = [Cooler(c) for c in range(1, len(items) + 1)]
        # Modbus
        self.opc = FloatModbusClient(host=self.host, port=SERVER_PORT, auto_open=True)
        # define modbus server host, port
        self.opc.host(self.host)
        self.opc.port(SERVER_PORT)
        
    #  @run_in_executor
    def get_temperature(self, c_index):
        try:
            if not self.opc.is_open():
                if not self.opc.open():
                    print("unable to connect to "+SERVER_HOST+":"+str(SERVER_PORT))
            
            value = 0.0
            if self.opc.is_open():
                value = self.opc.read_float_inp(c_index.num*2, 1)
                if value:
                    c_index.pv.Value = value[0]
                    c_index.pv.Fault = False
                else:
                    c_index.pv.Value = -111.1
                    c_index.pv.Fault = True
            
               
                value = 0.0
                value = self.opc.read_float(c_index.num*2-1, 1)
                if value:
                    c_index.sp = value[0]
                else:
                    c_index.sp = -111.1
                # TODO: необходимо считывать состояние из слова, а не из команды
                bits  = self.opc.read_coils((c_index.num-1)*2, 1)
                if bits:
                    c_index.StateOn = bits[0]
                else:
                    c_index.StateOn = False
                
            # print('pv', c_index.pv.Value, ', isFault', c_index.pv.Fault, ', sp', c_index.sp)
            
            for c_item in self.coolers_arr:
                if c_item.name == c_index.name:
                    c_item = c_index
                
        except Exception:
            traceback.print_exc()
            c_index.pv.Value = -321.1
            c_index.pv.Fault = True
            c_index.sp = -321.1
            c_index.State = -321.1
        return c_index.pv.Value

    def write_sp(self, sp, target):
        if self.opc.is_open():
            for c in self.coolers_arr:
                if c.name == target:
                    c.SetSP(sp)
                    self.opc.write_float(c.num*2-1, [float(c.sp)])

    def write_cmd_on(self, target):
        if self.opc.is_open():
            for c in self.coolers_arr:
                if c.name == target:
                    c.YOn()
                    self.opc.write_single_coil((c.num-1)*2, True)
                    self.opc.write_single_coil((c.num-1)*2+1, False)
                    
    def write_cmd_off(self, target):
        if self.opc.is_open():
            for c in self.coolers_arr:
                if c.name == target:
                    c.YOff()
                    self.opc.write_single_coil((c.num-1)*2, False)
                    self.opc.write_single_coil((c.num-1)*2+1, True)
