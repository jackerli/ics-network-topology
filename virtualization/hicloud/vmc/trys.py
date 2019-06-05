import libvirt
import time
conn = libvirt.openReadOnly(None)
dom = conn.lookupByUUIDString("82d73465-59e9-11e9-a7f1-52547246f1a9")
#state, maxMemory, memory, num_vcpu, cpuTime
vmiList = dom.info()
print vmiList[0]
time1 = vmiList[4]
time.sleep(1)
vmiList = dom.info()
time2 = vmiList[4]
print time2-time1
print (time2-time1)/(pow(10,7))

