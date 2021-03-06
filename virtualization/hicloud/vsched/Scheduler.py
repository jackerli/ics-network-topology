from ParseNet import *
from Utils import *
from ImportedModel import *
import Logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from xml.dom import minidom
import Server
import SOAPpy

logger = Logging.get_logger('hicloud.vsched.Scheduler')
class SchedulerClass:
    def func1(self, strs):
	logger.info("func1 is running")
	try:
		return strs
	except Exception as err:
		logger.error("func1 error:%s"%(str(err)))
		return "fuck"

    def __init__(self):
	try:
	    print "init a Scheduler class"
	    logger.info("init a Scheduler class")
	except Exception as err:
	    logger.error('********************SchedulerClass __init__ error: %s***********************'%(str(err)))
	
    def randomMac(self):
	logger.info("randomMac is running")
	Maclist = []
	for i in range(1,7):
	    RANDSTR = "".join(random.sample("0123456789abcdef",2))
	    Maclist.append(RANDSTR)
	randMac = ":".join(Maclist)
	return randMac

    def generateMac(self):
	logger.info("generateMac is running")
	session = self.getSession()
	MACs = session.query(Macs).all()
	mac_address = ""
	for MAC in MACs:
	    if MAC.status == 0:
		mac_address = MAC.address
		MAC.status = 1
		session.commit()
		break
	if mac_address=="":
	    mac_address = self.randomMac()
	session.close()
	logger.info("get a mac address: %s"%(mac_address))
	return mac_address

    def generateVMCid(self):
	logger.info("generateVMCid is running")
	session = self.getSession()
	vmcs = session.query(VirtualMachineContainer).all()
	vmcid = -1
	for vmc in vmcs:
	    if vmc.vmi_num < vmc.max_vmi_num:
		vmcid = vmc.id
		vmc.vmi_num = vmc.vmi_num + 1
		session.commit()
		break
	session.close()
	logger.info("get the vmcid: %s"%vmcid)
	return vmcid

    def completeXML(self, Settings, Uuid, Hostname, CpuCnt, Mem, NicCnt, DiskSize, OsType, OsVersion, SoftwareType, IsoPath, Vlan, MAC, DNS, VstoreIp):
	logger.info("completeXML is running")
	logger.info("Settings: %s"%Settings)
	logger.info("Uuid: %s, Hostname: %s, CpuCnt: %s, Mem: %s, NicCnt: %s, DiskSize: %s, OsType: %s, OsVersion: %s, SoftwareType: %s, IsoPath: %s, Vlan: %s, MAC: %s, DNS: %s"%(str(Uuid), str(Hostname), str(CpuCnt), str(Mem), str(NicCnt), str(DiskSize), str(OsType), str(OsVersion), str(SoftwareType), str(IsoPath), str(Vlan), str(MAC), str(DNS)))
	xmldoc = minidom.parseString(Settings.encode("utf-8"))
	xmldoc.getElementsByTagName('Uuid')[0].firstChild.replaceWholeText(Uuid)
	xmldoc.getElementsByTagName('Hostname')[0].firstChild.replaceWholeText(Hostname)
	xmldoc.getElementsByTagName('CpuCnt')[0].firstChild.replaceWholeText(CpuCnt)
	xmldoc.getElementsByTagName('Mem')[0].firstChild.replaceWholeText(Mem)
	xmldoc.getElementsByTagName('NicCnt')[0].firstChild.replaceWholeText(NicCnt)
	xmldoc.getElementsByTagName('DiskSize')[0].firstChild.replaceWholeText(DiskSize)
	xmldoc.getElementsByTagName('OsType')[0].firstChild.replaceWholeText(OsType)
	xmldoc.getElementsByTagName('OsVersion')[0].firstChild.replaceWholeText(OsVersion)
	xmldoc.getElementsByTagName('IsoPath')[0].firstChild.replaceWholeText(IsoPath)
	xmldoc.getElementsByTagName('SoftwareType')[0].firstChild.replaceWholeText(SoftwareType)
	xmldoc.getElementsByTagName('Vlan')[0].firstChild.replaceWholeText(Vlan)
	xmldoc.getElementsByTagName('MAC')[0].firstChild.replaceWholeText(MAC)
	xmldoc.getElementsByTagName('DNS')[0].firstChild.replaceWholeText(DNS)
	xmldoc.getElementsByTagName('VstoreIp')[0].firstChild.replaceWholeText(VstoreIp)
	re_settings = xmldoc.toxml()
	logger.info("Completed Settings: %s"%re_settings)
	return re_settings

    #delete vmi according to uuid, and recover corresponding attributes in vmc and mac
    def delVMI(self, uuid):
	    logger.info("delVMI is running")
	    try:
		    session = self.getSession()
		    vmis = session.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == uuid).all()
		    if len(vmis)==0:
			logger.error("no vmi with uuid %s"%(str(uuid)))
			return -1
		    virtual_machine_container_id = vmis[0].virtual_machine_container_id
		    logger.info("virtual_machine_container_id:%s of vmi uuid %s"%(str(virtual_machine_container_id), str(uuid)))
		    xml = vmis[0].settings
		    xmldoc = minidom.parseString(xml.encode("utf-8"))
		    mac_address = xmldoc.getElementsByTagName("MAC")[0].firstChild.data
		    logger.info("unoccupy mac_address:%s"%(str(mac_address)))
		    mac = session.query(Macs).filter(Macs.address == mac_address).all()[0]
		    mac.status = 0
		    vmc = session.query(VirtualMachineContainer).filter(VirtualMachineContainer.id == virtual_machine_container_id).all()[0]
		    vmc.vmi_num = vmc.vmi_num - 1
		    session.delete(vmis[0])
                    session.commit()
		    print "del vmi with uuid %s"%(str(uuid))
		    ip = vmc.address
                    soap = self.getSoap(ip, "8080", "vmi")
		    session.close()
		    res = soap.stopSVM(uuid)
	            res = soap.undeploySVM(uuid)
		    if res!=0:
			return -1
		    return 0
	    except Exception as e:
		    logger.info("fail to create the session to del vmi %s: %s"%(str(uuid), str(e)))
		    return -1

	#delete all vmis 
    def delAllvmis(self):
	    logger.info("delAllvmis is running")
	    try:
		   session = self.getSession()
		   vmis = session.query(VirtualMachineInstance).all()
		   for vmi in vmis:
			uuid = vmi.uuid
			self.delVMI(uuid)

		   vswitchs = session.query(Vswitch).all()
		   for vswitch in vswitchs:
			address = vswitch.ip
			self.delSwitchByaddr(str(address))
		   
		   session.close()
		   return 0
	    except Exception as e:
		   logger.info("fail to create the session to del all vmis: %s"%(str(e)))
		   return -1

    def getSoap(self, url, port, path):
	    logger.info("getSOAP is running")
	    try:
		    url = "http://"+str(url)+":"+str(port)+"/"+str(path)
		    soap = SOAPpy.SOAPProxy(url)
		    return soap
	    except Exception as e:
		    logger.info("fail to create the SOAP: %s"%(str(e)))
		    return None

    def getTap(self, ip):
	    logger.info("getTap is running")
	    tap_name = "-1"
	    try:
		   session = self.getSession()
		   vswitch = session.query(Vswitch).filter(Vswitch.ip == ip)[0]
		   if vswitch.vmi_num >= 2:
			raise Exception("no more available tap for vmi")
			return tap_name
		   vswitch.vmi_num = vswitch.vmi_num + 1
		   tap_name = "tap"+str(vswitch.vmi_num)
		   session.commit()
		   session.close()
		   return tap_name 
	    except Exception as e:
		   logger.info("fail to get tap_name: %s"%(str(e)))
		   return tap_name

    def getSession(self):
	    logger.info("getSession is running")
	    try:
		    engine = create_engine('mysql://debian-sys-maint:jAYKfnrf0JjY4Zz8@172.20.0.234/tryHicloud_db')
		    DBsession = sessionmaker(bind = engine)
		    session = DBsession()
		    return session
	    except Exception as e:
		    logger.info("fail to create the session: %s"%(str(e)))
		    return None

	#add VMI class instances into the database 
    def addVMIs(self, os_name, os_version, software_type, method):
	    logger.info("add VMIs is running. OsType: %s, OsVersion: %s, SoftwareType: %s"%(os_name, os_version, software_type))
	    session = self.getSession()
	    Uuid = GenUUID()
	    IsoPath = ""
	    if software_type.strip() == "PLC":
		Hostname = os_name.strip()+"-"+os_version.strip()+'-Server-'+software_type.strip()+'-'+Uuid.strip()
		if method.strip() == "iso":
			IsoPath = '/vmc160/'+os_name.strip()+"-"+os_version.strip()+'-Server.iso'
		else:
			IsoPath = '/vmc160/backups.iso'
	    else:
		Hostname = os_name.strip()+"-"+os_version.strip()+'-Desktop-'+software_type.strip()+'-'+Uuid.strip()
		if method.strip() == "iso":
			IsoPath = '/vmc160/'+os_name.strip()+"-"+os_version.strip()+'-Desktop.iso'
		else:
			IsoPath = '/vmc160/backups.iso'

	    CpuCnt = '1'
	    Mem = '256'
	    NicCnt = '1'
	    DiskSize = '1'
	    VstoreIP = '127.0.0.1'
	    vmc_id = self.generateVMCid()
	    VstoreIP = session.query(VirtualMachineContainer).filter(VirtualMachineContainer.id == vmc_id).all()[0].address
	    vstore_ip = VstoreIP
	    VstorePath = '/tmp/adtp-master/hicloud/vstore'
	    StoreType = 'local'
	    OsType = os_name
	    OsVersion = os_version
	    SoftwareType = software_type
	    Vlan = '0'
	    Address = '0.0.0.0'
	    Network = '255.255.255.0'
	    GateWay = '172.20.0.1'
	    MAC = self.generateMac()
	    DNS = '1.2.4.8'
	    Settings = '<vNode><Uuid>107b03a6-5d99-11e6-9477-000c29bf9897</Uuid><Type> </Type><Hostname>Ubuntu-Server-PLC</Hostname><Desc> </Desc><CpuCnt>1</CpuCnt><Mem>256</Mem><NicCnt>1</NicCnt><DiskSize>1</DiskSize><VstoreIp>127.0.0.1</VstoreIp><VstorePath>/tmp/adtp-master/hicloud/vstore</VstorePath><StorageType>local</StorageType><OsType>Ubuntu</OsType><OsVersion>16</OsVersion><SoftwareType>PLC</SoftwareType><vTemplateRef> </vTemplateRef><IsoPath>/vmc160/ubuntu-16.04.4-server-amd64.iso</IsoPath><NIC id=\'1\'><Vlan>0</Vlan><Address>0.0.0.0</Address><Netmask>255.255.255.0</Netmask><Gateway>172.20.0.1</Gateway><MAC>52:54:00:dc:f4:d8</MAC><DNS>1.2.4.8</DNS></NIC><Password> </Password></vNode>'
	    Settings = self.completeXML(Settings, Uuid, Hostname, CpuCnt, Mem, NicCnt, DiskSize, OsType, OsVersion, SoftwareType, IsoPath, Vlan, MAC, DNS, VstoreIP)
	    newVMI = VirtualMachineInstance(uuid = Uuid, hostname = Hostname, virtual_machine_container_id = vmc_id, cpu_cnt = CpuCnt, mem_total = Mem, nic_cnt = NicCnt, disk_total = DiskSize, ip = vstore_ip, store_type = StoreType, oper_system_type = OsType, oper_system_version = OsVersion, software_type = SoftwareType, settings = Settings)
	    session.add(newVMI)
	    session.commit()
	    session.close()

	#add Switch class instances into the database
	#construct br0, create taps and connect them to br0
    def addSwitchs(self):
	    logger.info("addSwitchs is running")
	    try:
		    session = self.getSession()
		    vmcs = session.query(VirtualMachineContainer).all()
		    for vmc in vmcs:
		        address = vmc.address
			soap = self.getSoap(address, 8080, "ovs")
			#print "......\n\naddSwitchs use func1:%s\n\n......\n"%str(soap.func1(1,2,3))
			soap.create_br0("ovs-vsctl")
			vswitch = session.query(Vswitch).filter(Vswitch.ip == str(address).strip())[0]
			for i in range(1, 3):
				tap_name = "tap"+str(i)
	    			soap.start_tap_by_name(0, tap_name)
				print "address: %s, tap_name: %s"%(str(address),str(tap_name))
			vswitch.tap_num = vswitch.tap_num + 2
			session.commit()
			logger.info("create br0 in vmc with ip address:%s"%(str(address)))
		    session.close()	

	    except Exception as e:
		    logger.info("fail to add switchs: %s"%str(e))

	#delete switch in the address
    def delSwitchByaddr(self, address):
	    logger.info("delSwitchs is running")
	    try:
		session = self.getSession()
		vswitch = session.query(Vswitch).filter(address == Vswitch.ip)[0]
		
		soap = self.getSoap(str(address), "8080", "ovs")
		soap.del_br0()
		
		print "delete br0 in address: %s"%(str(address))
		vswitch.tap_num = 0
		vswitch.vmi_num = 0
		session.commit()
		session.close()
	    except Exception as e:
		logger.info("fail to del switchs in address %s:%s"%(str(address), str(e)))
	
	#parse the topology net and add its devices into the database
    def addNet(self, xml):
		logger.info("addNet is running")
		device_names = ParseNet(xml)
		try:
		    engine = create_engine('mysql://debian-sys-maint:jAYKfnrf0JjY4Zz8@localhost/tryHicloud_db')
		    DBsession = sessionmaker(bind = engine)
		    session = DBsession()
		    MACs = session.query(Macs).all()
		    for MAC in MACs:
		        MAC.status = 0
		        session.commit()
		    VMCs = session.query(VirtualMachineContainer).all()
		    for VMC in VMCs:
		        VMC.vmi_num = 0
		        session.commit()

		    logger.info("create the session to mysql tryHicloud_db")
		except Exception as e:
		    logger.info("fail to create the session to mysql tryHicloud_db: %s"%str(e))
		for i in range(len(device_names)):
		    if i%2!=0:    #vmi 
		        logger.info("This is a vmi of type %s"%str(device_names[i]))
			self.addVMIs('ubuntu', '16', device_names[i], "image")
		    else:         #switch
		        logger.info("This is a switch") 
		session.close()

    def createVMIs(self, method):
	    logger.info("createVMIs is running")
	    session = self.getSession()
	    vmis = session.query(VirtualMachineInstance).all()
	    res = ""
	    try:
		if method == "iso":
			logger.info("createVMIs with iso")
		elif method == "image":
			logger.info("createVMIs with image")
			for vmi in vmis:
				ip = vmi.ip
				port = "8080"
				uuid = vmi.uuid
				xml = vmi.settings
				print xml
				name = vmi.hostname
				tap_name = self.getTap(str(ip))
				print "ip: %s, name: %s, tap_name: %s, uuid: %s"%(str(ip), str(name), str(tap_name), str(uuid))
				soap = self.getSoap(str(ip), port, "vmi")
		                logger.info("begin to create vim with uuid %s"%(str(uuid)))
		                res = res + " " + soap.createSVMimage(uuid ,xml, tap_name)
				logger.info("succeed to createSVM name:%s uuid:%s in address of %s"%(str(name), str(uuid), str(ip)))
		else:
			logger.error("createVMIS errors")
		session.close()
		return res
	    except Exception as e:
		logger.info("fail to create vmis: %s"%(str(e)))
		return "error in createVMIs"

    def deployNet(self, xml):
	logger.info("deployNet is running")
	self.delAllvmis()
	self.addNet(xml)
        self.addSwitchs()
        self.createVMIs("image")
        print "after deploying the net"
        self.getAll()
        print "... ..."
        return 0

	#delAllvmis(del all vmis and switchs) --> addNet --> addSwitchs --> createVMIs
    def deployFixedNet(self): 
	    logger.info("deployFixedNet is running")	        
	    xml = "<topology type='network'>\n\
	<name>tryNet</name>\n\
	<nodes>\n\
	<node name='HMI'></node>\n\
	<node name='Switch'></node>\n\
	<node name='Unity'></node>\n\
	<node name='AD'></node>\n\
	<node name='PLC'></node>\n\
	</nodes>\n\
	<links>\n\
	<link endpoint1='Switch' endpoint2='HMI'></link>\n\
	<link endpoint1='Switch' endpoint2='Unity'></link>\n\
	<link endpoint1='Switch' endpoint2='AD'></link>\n\
	<link endpoint1='Switch' endpoint2='PLC'></link>\n\
	</links>\n\
	</topology>"
	    self.addNet(xml)
	    
	    self.addSwitchs()
	    
	    res = self.createVMIs("image")
	    
            return res 	    

    def tryMain2(self):
	    self.getAll()
	#list all Mac
    def getAllmac(self):
		logger.info("getAllmac is running")
		try:
		    engine = create_engine('mysql://debian-sys-maint:jAYKfnrf0JjY4Zz8@localhost/tryHicloud_db')
		    DBsession = sessionmaker(bind = engine)
		    session = DBsession()
		    macs = session.query(Macs).all()
		    for mac in macs:
		        id = mac.id
		        status = mac.status
		        address = mac.address
		        print ("id:%s, status:%s, address:%s"%(str(id), str(status), str(address)))
		    session.close()
		    logger.info("create the session to mysql tryHicloud_db")
		except Exception as e:
		    logger.info("fail to create the session to mysql tryHicloud_db: %s"%str(e))

    def getAllvswitch(self):
		logger.info("getAllswitch is running")
		try:
			session = self.getSession()
			vswitchs = session.query(Vswitch).all()
			for vswitch in vswitchs:
				print ("vswitch_id:%s"%(str(vswitch.id)))
				print ("vmc_id:%s"%(str(vswitch.virtual_machine_container_id)))
				print ("vswitch_ip:%s"%(str(vswitch.ip)))
				print ("tap_num:%s"%(str(vswitch.tap_num)))
				print ("vmi_num:%s"%(str(vswitch.vmi_num)))
				session.commit()
			session.close()
		except Exception as e:
		    logger.info("fail to create the session to mysql tryHicloud_db: %s"%str(e))


	#list all virtualmachinecontainers
    def getAllvmc(self):
		logger.info("getAllvmc is running")
		try:
		    engine = create_engine('mysql://debian-sys-maint:jAYKfnrf0JjY4Zz8@localhost/tryHicloud_db')
		    DBsession = sessionmaker(bind = engine)
		    session = DBsession()
		    vmcs = session.query(VirtualMachineContainer).all()
		    for vmc in vmcs:
		    	id = vmc.id
		        uuid = vmc.uuid
			hostname = vmc.hostname
			address = vmc.address
		        status = vmc.status
			running_time = vmc.running_time
			cpu_num = vmc.cpu_num
			cpu_usage = vmc.cpu_usage
			mem_total = vmc.mem_total
			mem_free = vmc.mem_free		
			disk_total = vmc.disk_total
			disk_free = vmc.disk_free
			nics_num = vmc.nics_num
			vmi_num = vmc.vmi_num
			max_vmi_num = vmc.max_vmi_num
			print ("id:%s, uuid:%s, hostname:%s, address:%s, status:%s, running_time:%s, cpu_num:%s, cpu_usage:%s, mem_total:%s, mem_free:%s, disk_total:%s, disk_free:%s, nics_num:%s, vmi_num:%s, max_vmi_num:%s"%(str(id), str(uuid), str(hostname), str(address), str(status), str(running_time), str(cpu_num), str(cpu_usage), str(mem_total), str(mem_free), str(disk_total), str(disk_free), str(nics_num), str(vmi_num), str(max_vmi_num)))
		        #print ("settings:%s"%settings)
		    session.close()
		    logger.info("create the session to mysql tryHicloud_db")
		except Exception as e:
		    logger.info("fail to create the session to mysql tryHicloud_db: %s"%str(e))

	#list all virtualmachineinstances
    def getAllvmi(self):
		logger.info("getAllvmi is running")
		try:
		    session = self.getSession()
		    vmis = session.query(VirtualMachineInstance).all()
		    #Settings, Uuid, Hostname, CpuCnt, Mem, NicCnt, DiskSize, OsType, OsVersion, SoftwareType, IsoPath, Vlan, MAC, DNS
		    logger.info("There are %s vmis in the system"%(str(len(vmis))))
		    for vmi in vmis:
		        id = vmi.id
		        uuid = vmi.uuid
		        hostname = vmi.hostname
			virtual_machine_container_id = vmi.virtual_machine_container_id
		        status = vmi.status
		        ip = vmi.ip
			cpu_cnt = vmi.cpu_cnt
			mem = vmi.mem_total
			nic_cnt = vmi.nic_cnt
			disk_size = vmi.disk_total
			os_type = vmi.oper_system_type
			os_version = vmi.oper_system_version
			software_type = vmi.software_type
			settings = vmi.settings
		        print ("id:%s, uuid:%s, hostname:%s, virtual_machine_container_id:%s, status:%s, ip:%s, cpu_cnt:%s, mem:%s, nic_cnt:%s, disk_size:%s, os_type:%s, os_version:%s, software_type:%s"%(str(id), str(uuid), str(hostname), str(virtual_machine_container_id), str(status), str(ip), str(cpu_cnt), str(mem), str(nic_cnt), str(disk_size), str(os_type), str(os_version), str(software_type)))
		        print ("settings:%s"%(str(settings)))
		    session.close()
		    logger.info("create the session to mysql tryHicloud_db")
		except Exception as e:
		    logger.error("fail to get all vmi: %s"%(str(e)))

    def getAll(self):
		logger.info("get All is running")
		try:
			print "... ...all info... ..."
			self.getAllvmi()
	    		print "... ..."
	    		self.getAllvmc()
	    		print "... ..."
	    		self.getAllmac()
	    		print "... ..."
	    		self.getAllvswitch()
	    		print "... ..."
		except Exception as e:
		   logger.error("fail to get all information:%s"%(str(e)))

    def infoCluster(self):
		logger.info("infoCluster is running")
		dict_info = {'cpu_usage':0, 'mem_usage':0, 'disk_usage':0, 'mem_total':0, 'disk_total':0, 'phy_on_num':0, 'phy_off_num':0}
		try:
			session = self.getSession()
			vmcs = session.query(VirtualMachineContainer).all()
			cnt = 1
                        for vmc in vmcs:
				address = vmc.address
				soap = getSoap(str(address), "8080", "vmi")
				dict_tmp = soap.infoVmc()
				for key,value in dict_tmp.items():
					if key == 'cpu_usage':
						dict_info['cpu_usage'] = (dict_info['cpu_usage'] + dict_tmp['cpu_usage'])/cnt
					else:
						dict_info[key] = dict_info[key] + value
				cnt = cnt + 1
			session.close()
			return dict_info
		except Exception as e:
			logger.error("infoCluster error:%s"%(str(e)))
			return dict_info
    def infoVcluster(self):
                logger.info("infoVcluster is running")
                dict_info = {'name':'', 'uuid':'', 'cpu_usage':0, 'status':-1, 'mem_total':0, 'disk_total':60}
		try:
                        session = self.getSession()
                        vmcs = session.query(VirtualMachineContainer).all()
                        cnt = 1
                        for vmc in vmcs:
                                address = vmc.address
                                soap = getSoap(str(address), "8080", "vmi")
				vmis = session.query(VirtualMachineInstance).all()
				cnt = 1
				for vmi in vmis:
					uuid = vmi.uuid
                                	dict_tmp = soap.infoVmc(uuid)
                                	for key,value in dict_tmp.items():
                                        	if key == 'cpu_usage':
                                                	dict_info['cpu_usage'] = (dict_info['cpu_usage'] + dict_tmp['cpu_usage'])/cnt
                                        	else:
                                                	dict_info[key] = dict_info[key] + value
                                	cnt = cnt + 1
                        session.close()
                        return dict_info
                except Exception as e:
                        logger.error("infoVcluster error:%s"%(str(e)))
                        return dict_info
    def replaceSome(dict1, dict2):
	logger.info("replaceSome is running")
	try:
		for key1, value1 in dict1.items():
			for key2, value2 in dict2.items():
				if str(key1) == str(key2):
					dict1[key1] = value2
		return dict1
	except Exception as e:
		logger.error("replaceSome error:%s"%(str(e)))
		return dict1
    def infoVmclist(self):
	#name, phy_ip, cpu_usage, mem_total, disk_total, phy_on_num, phy_off_num, phy_status
	logger.info("infoVmclist is running")
	rel = []
	try:
		session = self.getSession()
		vmcs = session.query(VirtualMachineContainer).all()
                for vmc in vmcs:
			dict_tmp1 = {'name':'', 'phy_ip':'', 'cpu_usage':0, 'mem_total':0, 'disk_total':0, 'phy_on_num':1, 'phy_off_num':0, 'phy_status':1}
			name = vmc.name
			phy_ip = vmc.address
			soap = self.getSoap(str(phy_ip), "8080", "vmi")
			dict_tmp2 = soap.infoVmc()
			dict_tmp1 = self.replaceSome(dict_tmp1, dict_tmp2)
			dict_tmp1['name'] = name
			dict_tmp1['phy_ip'] = phy_ip
			rel.append(dict_tmp1)
		session.close()
		return rel
	except Exception as e:
		logger.error("infoVmclist error: %s"%(str(e)))
		return rel

    def infoVmisByIp(self, name, ip):
	logger.info("infoVmisByIp is running: name %s ip %s"%(str(name),str(ip)))
	rel = []
	try:
		session = self.getSession()
		vmis = session.query(VirtualMachineInstance).filter(VirtualMachineInstance.ip == ip).all()
		soap = self.getSoap(str(ip), "8080", "vmi")
		for vmi in vmis:
			dict_tmp1 = {'name':'', 'ip':'', 'host_loc':'', 'create_time':time.strftime("%Y-%m-%d %X",time.localtime())
, 'status':0, 'uuid':'', 'cpu_usage':0}
			name = vmi.name
			ip = vmi.ip
			uuid = vmi.uuid
			create_time = vmi.created_at
			dict_tmp2 = soap.infoVmi(uuid)
			dict_tmp1 = self.replaceSome(dict_tmp1, dict_tmp2)
			dict_tmp1['ip'] = ip
			dict_tmp1['create_time'] = create_time
			dict_tmp1['host_loc'] = ip
			rel.append(dict_tmp1)
		session.close()
		return rel	
	except Exception as e:
		logger.error("infoVmisBYIp error:%s"%(str(e)))
		return rel

    def infoVmis(self):
	logger.info("infoVmis is running")
	rel = []
	try:
		session = self.getSession()
		vmcs = session.query(VirtualMachineContainer).all()
		for vmc in vmcs:
			name = vmc.hostname
			ip = vmc.address
			rel_tmp = self.infoVmisByIp(name, ip)
			rel.extend(rel_tmp)
		session.close()
		return rel
	except Exception as e:
		logger.error("infoVmis error:%s"%(str(e)))
		return rel

    def start_vmi(self, uuid, ip):
	logger.info("start_vmi is running")
	try:
		session = self.getSession()
		vmi = session.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == uuid).all()
		if len(vmi) == 0:
			logger.error("no vmi with uuid %s"%(str(uuid)))
			return 0
		ip = vmi.ip
		soap = self.getSoap(str(ip), "8080", "vmi")
		res = soap.startSVM(uuid)
		if res != 0:
			return 0
		session.close()
		return 1
	except Exception as e:
		logger.error("start_vmi: %s"%(str(e)))
		return 0

   def pause_vmi(self, uuid, ip):
        logger.info("pause_vmi is running")
        try:
		session = self.getSession()
                vmi = session.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == uuid).all()
                if len(vmi) == 0:
                        logger.error("no vmi with uuid %s"%(str(uuid)))
                        return 0
		ip = vmi.ip
                soap = self.getSoap(str(ip), "8080", "vmi")
                res = soap.pauseSVM(uuid)
		if res != 0:
			return 0
                session.close()
                return 1
        except Exception as e:
                logger.error("pause_vmi: %s"%(str(e)))
		return 0

   def resume_vmi(self, uuid, ip):
        logger.info("resume_vmi is running")
        try:
		session = self.getSession()
                vmi = session.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == uuid).all()
                if len(vmi) == 0:
                        logger.error("no vmi with uuid %s"%(str(uuid)))
                        return 0
		ip = vmi.ip
                soap = self.getSoap(str(ip), "8080", "vmi")
                res = soap.resumeSVM(uuid)
                if res != 0:
                        return 0
                session.close()
                return 1
        except Exception as e:
                logger.error("resume_vmi: %s"%(str(e)))
		return 0
   def close_vmi(self, uuid, ip):
        logger.info("close_vmi is running")
        try:
		session = self.getSession()
                vmi = session.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == uuid).all()
                if len(vmi) == 0:
                        logger.error("no vmi with uuid %s"%(str(uuid)))
                        return 0
		ip = vmi.ip
                soap = self.getSoap(str(ip), "8080", "vmi")
                res = soap.stopSVM(uuid)
                if res != 0:
                        return 0
                session.close()
                return 1
        except Exception as e:
                logger.error("close_vmi: %s"%(str(e)))
		return 0
'''
sch = SchedulerClass()
sch.getAll()
'''

#session = sch.getSession()
#vswitchs = session.query(Vswitch).all()
#for vswitch in vswitchs:
#    address = vswitch.ip
#    sch.delSwitchByaddr(str(address))
#session.close()
'''
#sch.addSwitchs()
sch.deployFixedNet()
sch.getAll()
'''
