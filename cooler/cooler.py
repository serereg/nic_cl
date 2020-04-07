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
    sp = 0
    pv = Parameter('') # Parameter for control
    TagControl = ''
    TagSP = ''
    ControlString = ""
    StateOn = False
    def __init__(self, num):
        self.num = num
        self.name = "CKT" + str(num)
        print(self.name)
        self.TagControl = 'OPC.' + self.name + '.Control'
        self.TagYOn = 'Request1.'+'TIC' + str(num) + '_YOn'
        self.TagYOff = 'Request1.'+'TIC' + str(num) + '_YOff'
        self.pv = Parameter('Request2.'+'TIC' + str(num) + '_PV')
        self.TagSP = 'Request3.'+'TIC' + str(num) + '_SP'
        self.TagState = 'Request3.'+'TIC' + str(num) + '_STATE'
        self.State = 0
        self.Alarm = False
        self.CmdOn = False
        self.CmdOff = False
        
    def is_set(self, x, n):
        return x & 1 << n != 0
        
    def YOn(self):
        print('YOn')
        self.CmdOn = True
        self.CmdOff = False
        
    def YOff(self):
        print('YOff')
        self.CmdOn = False
        self.CmdOff = True

    def SetSP(self, nsp):
        self.sp = nsp
        print('SetSP')

    def GetPV(self):
        # print('GetPV')
        # self.pv.Value = self.sp # imitation
        return self.pv.Value
        
    def isOn(self):
        return self.StateOn

    def update_state_on(self):
        self.StateOn = self.is_set(self.State,0)

    def isFault(self):
        self.pv.Fault = self.is_set(self.State,1)
        return self.pv.Fault

    def isAlarm(self):
        self.Alarm = self.is_set(self.State,2)
        return self.Alarm

#def main():
#    CKT1 = Cooler('1')
#    print(CKT1.PV.Value)

#main()

if __name__ == '__main__':
    C1 = Cooler(1)
    pass
