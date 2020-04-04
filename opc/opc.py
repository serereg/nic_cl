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

SERVER_HOST = "192.168.0.240"
SERVER_PORT = 502

def run_in_executor(f):
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, f, *args, **kwargs)
    return wrapper

class OPC:
    map_modbus_coils_on = [1,3,5,7,9,11,13,15,17,19,21,23]
    map_modbus_pv = [2,6,10,14,18,22,26,30,34,38,42,46]
    map_modbus_state = [3,7,11,15,19,23,27,31,35,39,43,47]
    map_modbus_sp = [1,3,5,7,9,11,13,15,17,19,21,23,25]
    def __init__(self, host, items):
        self.host = host
        self.items = items
        self.coolers_arr = [Cooler(c) for c in range(1, len(items) + 1)]
        # Modbus
        self.opc = FloatModbusClient(host=self.host, port=SERVER_PORT, auto_open=True)
        # define modbus server host, port
        self.opc.host(SERVER_HOST)
        self.opc.port(SERVER_PORT)
        
    #  @run_in_executor
    def get_temperature(self, c_index):
        try:
            if not self.opc.is_open():
                if not self.opc.open():
                    str_err = "unable to connect to "+SERVER_HOST+":"+str(SERVER_PORT)
                    raise Exception(str_err)
            
            if self.opc.is_open():
                
                value = []
                value = self.opc.read_float_inp(self.map_modbus_pv[c_index.num-1], 1)
                if value:
                    c_index.pv.Value = value[0]
                    c_index.pv.Fault = False
                else:
                    value = self.opc.read_float_inp(self.map_modbus_pv[c_index.num-1], 1)
                    if value:
                        c_index.pv.Value = value[0]
                        c_index.pv.Fault = False
                    else:
                        c_index.pv.Value = -111.1
                        c_index.pv.Fault = True
            
               
                value = 0.0
                value = self.opc.read_float(self.map_modbus_sp[c_index.num-1], 1)
                if value:
                    c_index.sp = value[0]
                else:
                    c_index.sp = -111.1

                value = 0.0
                value = self.opc.read_input_registers(self.map_modbus_state[c_index.num-1], 2)
                if value:
                    c_index.State = value[0] | (value[1] << 16)
                else:
                    c_index.State = 0
                c_index.update_state_on()
                c_index.isFault()
                c_index.isAlarm()
                # TODO: необходимо считывать состояние из слова, а не из команды
                # bits  = self.opc.read_coils(self.map_modbus_coils_on[c_index.num-1], 1)
                # if bits:
                #     c_index.StateOn = bits[0]
                # else:
                #     c_index.StateOn = False
                
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
                    self.opc.write_float(self.map_modbus_sp[c.num-1], [float(c.sp)]) # c.num*2-1

    def write_cmd_on(self, target):
        if self.opc.is_open():
            for c in self.coolers_arr:
                if c.name == target:
                    print(c.name, c.num, self.map_modbus_coils_on[c.num] )
                    c.YOn()
                    self.opc.write_single_coil(self.map_modbus_coils_on[c.num-1], True)
                    self.opc.write_single_coil(self.map_modbus_coils_on[c.num-1]+1, False)
                    
    def write_cmd_off(self, target):
        if self.opc.is_open():
            for c in self.coolers_arr:
                if c.name == target:
                    print(c.name, c.num, self.map_modbus_coils_on[c.num]+1 )
                    c.YOff()
                    self.opc.write_single_coil(self.map_modbus_coils_on[c.num-1], False)
                    self.opc.write_single_coil(self.map_modbus_coils_on[c.num-1]+1, True)
