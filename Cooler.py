
class Parameter:
    Value = 0
    Fault = False
    TagName = "OPC.Item"
    def __init__(self, name):
        self.TagName = name
        #print(self.TagName)
    

class Cooler:
    """Управление охладителем"""
    num = 1 # cooler num
    name = "CKT" # cooler name
    SP = 0
    PV = Parameter('') # Parameter for control
    TagControl = ''
    TagSP = ''
    ControlString = ""
    def __init__(self, num):
        self.num = num
        name = "CKT" + num
        self.PV = Parameter(name)
        self.TagControl = 'OPC.' + name + '.Control'
        self.TagSP = 'OPC.' + name + '.SP'
        pass
    
    def YOn(self):
        pass
    def YOff(self):
        pass
    def SetSP(self):
        pass
    def GetPV(self):
        return self.PV.Value
        

def main():
    CKT1 = Cooler('1')
    
    
    print(CKT1.PV.Value)

main()

