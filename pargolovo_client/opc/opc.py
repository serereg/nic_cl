# for workin with opc
import OpenOPC
import pywintypes
from Cooler import Cooler

def run_in_executor(f):
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, f, *args, **kwargs)
    return wrapper

class OPC:
    def __init__(self, base_name, items):
        self.base_name = base_name
        self.items = items
        self.coolers_arr = [Cooler(c) for c in range(1, len(items) + 1)]
        # Connect to OPC
        pywintypes.datetime = pywintypes.TimeType
        self.opc = OpenOPC.client()
        print(self.opc.servers())
        self.opc.connect(self.base_name)

    #  @run_in_executor
    def get_temperature(self, c_index):
        try:
            # for c in self.coolers_arr:
            #     if c.name == index:
                    # print(c.pv.TagName + '\n')
            self.opc = OpenOPC.client()
            self.opc.connect(self.base_name)
            print('--------------------'+c_index.pv.TagName)
            opc_package = self.opc.read(c_index.pv.TagName)
            print('--------------------'+c_index.pv.TagName)
            self.opc.close()
            print(opc_package)
            if opc_package[1] == 'Good':
                c_index.pv.Value = opc_package[0]
                c_index.pv.Fault = False
            else:
                c_index.pv.Value = -111.1
                c_index.pv.Fault = True
                
            self.opc = OpenOPC.client()
            self.opc.connect(self.base_name)
            opc_package = self.opc.read(c_index.TagSP)
            self.opc.close()
            if opc_package[1] == 'Good':
                c_index.sp = opc_package[0]
            else:
                c_index.sp = -111.1

                    # opc_package = self.opc.read(c.TagState)
                    # if (opc_package[1] == 'Good'):
                    #     c.State = opc_package[0]
                    # else:
                    #     c.State = -666.6
                    # break

        except Exception:
            traceback.print_exc()
            c_index.pv.Value = -321.1
            c_index.pv.Fault = True
            c_index.sp = -321.1
            c_index.State = -321.1
        return c_index.pv.Value

    def write_sp(self, sp, target):
        self.opc = OpenOPC.client()
        self.opc.connect(self.base_name)
        for c in self.coolers_arr:
            if c.name == target:
                c.SetSP(sp)
                self.opc.write((c.TagSP, c.sp))
        self.opc.close()

    def write_cmd_on(self, target):
        self.opc = OpenOPC.client()
        self.opc.connect(self.base_name)
        for c in self.coolers_arr:
            if c.name == target:
                c.YOn()
                print(c.StateOn)
                self.opc.write((c.TagYOn, c.StateOn))
                self.opc.write((c.TagYOff, not c.StateOn))
        self.opc.close()

    def write_cmd_off(self, target):
        self.opc = OpenOPC.client()
        self.opc.connect(self.base_name)
        for c in self.coolers_arr:
            if c.name == target:
                c.YOff()
                print(c.StateOn)
                self.opc.write((c.TagYOn, c.StateOn))
                self.opc.write((c.TagYOff, not c.StateOn)) #c.StateOn
        self.opc.close()
