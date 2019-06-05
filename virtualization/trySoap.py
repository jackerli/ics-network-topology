import SOAPpy
url = '172.20.0.234'
port = '8080'
path = 'sch'
url = "http://"+str(url)+":"+str(port)+"/"+str(path)
soap = SOAPpy.SOAPProxy(url)
#172.20.0.234 ubuntu-16-Desktop-HMI-b66055a0-63fe-11e9-a3f1-52540028f1a9 172.20.0.234 ubuntu-16-Desktop-Unity-b66055a1-63fe-11e9-a3f1-52540028f1a9 172.20.0.235 ubuntu-16-Desktop-AD-b66055a2-63fe-11e9-a3f1-52540028f1a9 172.20.0.235 ubuntu-16-Server-PLC-b66055a3-63fe-11e9-a3f1-52540028f1a9
uuids = ['054b2450-7efe-11e9-a2fa-a0369f85b584','054b2451-7efe-11e9-a2fa-a0369f85b584','054b2452-7efe-11e9-a2fa-a0369f85b584','054b2453-7efe-11e9-a2fa-a0369f85b584']
ips = ['172.20.0.234','172.20.0.234','172.20.0.235','172.20.0.235']
'''
for i in range(0,4):
	print soap.pause_vmi(uuids[i], ips[i])
for i in range(0,4):
        print soap.resume_vmi(uuids[i], ips[i])
for i in range(0,4):
        print soap.close_vmi(uuids[i], ips[i])
for i in range(0,4):
        print soap.start_vmi(uuids[i], ips[i])
'''
#print soap.add_firewall(uuids[0], '2')
#print soap.add_firewall(uuids[1], '3')
#print soap.delete_firewall(uuids[0])
#print soap.delete_firewall(uuids[1])
#print soap.delAllvmis()
#print soap.deployFixedNet()
#print soap.add_mirrors()
#print soap.del_mirror()
#print soap.del_firewall('73df8dac-68d8-11e9-a2fa-a0369f85b584')
#print soap.add_firewall('73df8dad-68d8-11e9-a2fa-a0369f85b584')
#print soap.del_firewall('73df8dad-68d8-11e9-a2fa-a0369f85b584')
soap.getAll()
#soap.infoVmis()
