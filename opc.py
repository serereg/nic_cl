import asyncio
from concurrent.futures import ThreadPoolExecutor
# from threading import Thread
import time
import traceback

from cooler.cooler import Cooler
from pyModbusTCP.client import ModbusClient
from pyModbusTCP import utils
from utils import timer

# class OPC(Thread, ModbusClient):
class OPC(ModbusClient):
    map_modbus_coils_on = (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
    map_modbus_pv = (2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46)
    map_modbus_state = (3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47)
    map_modbus_sp = (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25)
    map_modbus_sp_out = [49,51,53,55,57,59,61,63,65,67,69,71]

    def __init__(self, host, port, cooler_count):
        ModbusClient.__init__(self, host=host, port=port, auto_open=True)
        # Thread.__init__(self)

        self._host = host
        self._port = port
        self.coolers = [Cooler(c) for c in range(1, cooler_count+1)]
        # Modbus
        self.timeout(2)
        self.running = False

    def read_float(self, address, number=1):
        reg_l = self.read_holding_registers(address, number * 2)
        if reg_l:
            return [utils.decode_ieee(f) for f in utils.word_list_to_long(reg_l)]

    def read_float_inp(self, address, number=1):
        reg_l = self.read_input_registers(address, number * 2)
        if reg_l:
            return [utils.decode_ieee(f) for f in utils.word_list_to_long(reg_l)]

    def write_float(self, address, floats_list):
        b32_l = [utils.encode_ieee(f) for f in floats_list]
        b16_l = utils.long_list_to_word(b32_l)
        return self.write_multiple_registers(address, b16_l)

    @timer(5)
    async def update(self):
        print("--opc update--")
        for cooler in self.coolers:
            
            try:
                if not self.is_open():
                    if not self.open():
                        str_err = f"unable to connect to {self._host}:{self._port}"
                        raise Exception(str_err)

                for i in range(2):
                    value = self.read_float_inp(self.map_modbus_pv[cooler.num-1], 1)
                    if value:
                        cooler.pv.Value = value[0]
                        cooler.pv.Fault = False
                        break
                else:
                    cooler.pv.Value = -111.1
                    cooler.pv.Fault = True

                value = 0.0
                value = self.read_float_inp(self.map_modbus_sp_out[cooler.num-1]+1, 1)
                if value:
                    cooler.sp = value[0]
                else:
                    cooler.sp = -112.2

                value = self.read_input_registers(self.map_modbus_state[cooler.num-1], 2)
                cooler.State = value[0] | (value[1] << 16) if value else 0 
                
                cooler.update_state_on()
                cooler.isFault()
                cooler.isAlarm()
                # TODO: необходимо считывать состояние из слова, а не из команды
                # bits = self.read_coils(self.map_modbus_coils_on[cooler.num-1], 1)
                # cooler.StateOn = bits[0] if bits else False
                    
                print(cooler.name, cooler.pv.Value, cooler.pv.Fault, cooler.sp)
                
            except Exception:
                # traceback.print_exc()
                cooler.pv.Value = -321.1
                cooler.pv.Fault = True
                cooler.sp = -321.1
                cooler.State = 65535
        
        #time.sleep(10)

    def start(self, loop):
            return (
                loop.create_task(self.update()),
            )

    # def run(self):
    #     self.running = True
    #     while self.running:
    #         self.update()

    # def stop(self):
    #     self.running = False

    def write_sp(self, sp, target):
        if self.is_open():
            for c in self.coolers:
                if c.name == target:
                    c.SetSP(sp)
                    self.write_float(self.map_modbus_sp[c.num-1], [float(c.sp)]) # c.num*2-1
                    self.write_float(self.map_modbus_sp[c.num-1], [float(c.sp)]) # c.num*2-1

    def write_cmd_on(self, target):
        if self.is_open():
            for c in self.coolers:
                if c.name == target:
                    print(c.name, c.num, self.map_modbus_coils_on[c.num] )
                    c.YOn()
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1], True)
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1]+1, False)
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1], True)
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1]+1, False)
                    
    def write_cmd_off(self, target):
        if self.is_open():
            for c in self.coolers:
                if c.name == target:
                    print(c.name, c.num, self.map_modbus_coils_on[c.num]+1 )
                    c.YOff()
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1], False)
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1]+1, True)
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1], False)
                    self.write_single_coil(self.map_modbus_coils_on[c.num-1]+1, True)
