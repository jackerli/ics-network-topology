import Config
import Logging
from Server import ServerClass
from Openvswitch import Openvswitch

logger = Logging.get_logger('hicloud.vmc.Plugin')

__obj_vmi = None
__obj_ovs = None



def init():          ###(daemon_config):
    logger.info("hicloud.vmc.plugins.init is running")
    config = Config.load(str('/vmc160/hicloud/vmc.yaml'))
    ###general_config = Config.load(project_path('/etc/hicloud/general.yaml'))
    ###config["portal_url"] = general_config["portal_url"]
    # this should dispatch 'hicloud.vmc.*' to individual log file
    Logging.get_logger('hicloud.vmc')   ###filename=config['log_file'])

    logger.debug('initializing %s' % __name__)
    global __obj_vmi
    if __obj_vmi:
        logger.error('reinitialized of vm is not supported')
        return
    __obj_vmi = ServerClass()

    global __obj_ovs
    if __obj_ovs:
        logger.error('reinitialized of ovs is not supported')
        return
    __obj_ovs = Openvswitch()

    # try:
    #    external_address = daemon_config['external_address']
    # except Exception, e:
    #    logger.fatal('unable to get external_address from daemon: %s' % str(e))

    return [__obj_vmi, __obj_ovs]

def fini():
    global __obj_vmi
    del __obj_vmi

    global __obj_ovs
    del __obj_ovs


def soap_mods():
    soap_dict = {'vmi':None, 'ovs':None}
    global __obj_vmi
    soap_dict['vmi'] = __obj_vmi
    global __obj_ovs
    soap_dict['ovs'] = __obj_ovs
    return soap_dict

def wsgi_mods():
    return {}

def tryMain():
	debug_Server = init()
	'''
	uuid = '107b03a6-5d99-11e6-9477-000c29bf9837'
        xml = '<vNode><Uuid>107b03a6-5d99-11e6-9477-000c29bf9837</Uuid><Type> </Type><Hostname>Ubuntu-Server-PLC</Hostname><Desc> </Desc><CpuCnt>1</CpuCnt><Mem>256</Mem><NicCnt>1</NicCnt><DiskSize>1</DiskSize><VstoreIp>127.0.0.1</VstoreIp><VstorePath>/tmp/adtp-master/hicloud/vstore</VstorePath><StorageType>local</StorageType><OsType>Ubuntu</OsType><OsVersion>16</OsVersion><SoftwareType> </SoftwareType><vTemplateRef> </vTemplateRef><IsoPath>/vmc160/ubuntu-16.04.4-server-amd64.iso</IsoPath><NIC id=\'1\'><Vlan>0</Vlan><Address>0.0.0.0</Address><Netmask>255.255.255.0</Netmask><Gateway>172.20.0.1</Gateway><MAC>52:54:00:dc:f4:d7</MAC><DNS>1.2.4.8</DNS></NIC><Password> </Password></vNode>'
	debug_Server.createSVM(uuid, xml)
        debug_Server.startSVM(uuid)

	xml = '<vNode><Uuid>107b03a6-5d99-11e6-9477-000c29bf9897</Uuid><Type> </Type><Hostname>Ubuntu-Server-PLC</Hostname><Desc> </Desc><CpuCnt>1</CpuCnt><Mem>256</Mem><NicCnt>1</NicCnt><DiskSize>1</DiskSize><VstoreIp>127.0.0.1</VstoreIp><VstorePath>/tmp/adtp-master/hicloud/vstore</VstorePath><StorageType>local</StorageType><OsType>Ubuntu</OsType><OsVersion>16</OsVersion><SoftwareType>PLC</SoftwareType><vTemplateRef> </vTemplateRef><IsoPath>/vmc160/ubuntu-16.04.4-server-amd64.iso</IsoPath><NIC id=\'1\'><Vlan>0</Vlan><Address>0.0.0.0</Address><Netmask>255.255.255.0</Netmask><Gateway>172.20.0.1</Gateway><MAC>52:54:00:dc:f4:d8</MAC><DNS>1.2.4.8</DNS></NIC><Password> </Password></vNode>'
        debug_Server.createSVMimage(uuid, xml)
	debug_Server.startSVM(uuid)
	'''
