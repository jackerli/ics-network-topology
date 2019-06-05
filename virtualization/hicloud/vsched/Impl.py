# -*- coding: utf-8 -*-

import random
import threading

import commands
import pexpect
from StringIO import StringIO
from sqlalchemy.sql.expression import and_, or_

from Utils import GenUUID
from Interface import Interface
from Model import *

logger = Logging.get_logger('hicloud.vsched.Impl')

tableNames = {
    VmTemp: 'VM Template',
    VirtualClusterInstance: 'vCluster Instance',
    VirtualMachineInstance: 'VM Instance',
    Storage: 'vStore'
}

tableMapper2Key = {
    VmTemp: 'vTemplate',
    VirtualMachineInstance: 'VM',
    Storage: 'vStore',
    PhysicalCluster: 'pCluster'
}

templateKey2Mapper = {'vTemplate': VmTemp}
templateMappers = templateKey2Mapper.values()

instanceKey2Mapper = {
    'VM': VirtualMachineInstance,
    'VMC': VirtualMachineContainer,
    'VMT': VmTemp,
    'vStore': Storage,
    'pCluster': PhysicalCluster
}
instanceMappers = instanceKey2Mapper.values()


class Getter:

    def __init__(self, mapper_dict):
        self.mappers = mapper_dict.values()
        self.mapper_dict = mapper_dict
        self.reverse_dict = {}
        for k, v in mapper_dict.items():
            self.reverse_dict[v] = k

    # 获取待执行对象及记录ID
    def to_key(self, obj):
        return '%s@%d' % (self.reverse_dict[type(obj)], obj.id)

    # 获取待执行对象的记录
    def by_key(self, key, session):
        key_type, strid = key.split('@')
        try:
            id = int(strid)
            mapper = self.mapper_dict[key_type]
            obj = session.query(mapper).get(id)
            if not obj:
                raise LookupError, 'template with id %d not found' % id
            return obj
        except ValueError:
            raise LookupError, 'bad id value %s' % strid
        except KeyError:
            raise LookupError, 'bad key type %s' % key_type

    # 获取第一个满足uuid的待执行对象记录
    def by_uuid(self, uuid, session):
        rset = self.by_uuids(uuid, session)
        if len(rset) != 1:
            raise LookupError, 'bad uuid %s, found %d record alike' % (uuid, len(rset))
        return rset[0]

    # 获取所有满足uuid的待执行对象记录
    def by_uuids(self, uuid, session):
        if len(uuid) != 36:
            newuuid = uuid[:35] + '%'
        else:
            newuuid = uuid
        rset = []
        for mapper in self.mappers:
            if not hasattr(mapper, 'uuid'):
                logger.info("5")
                continue
            if '%' in newuuid:
                logger.info("6")
                expr = mapper.uuid.like(newuuid)
            else:
                logger.info("7")
            rset.append(session.query(mapper).filter(mapper.uuid == newuuid))
        logger.info(rset)
        return rset


TemplateGetter = Getter(templateKey2Mapper)
InstanceGetter = Getter(instanceKey2Mapper)


class ImplError(Exception):
    pass


def exceptionWrapper(fun):
    def __wrapper(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except ImplError:
            raise
        except Exception as e:
            logger.exception(e)
            raise ImplError, e.message

    return __wrapper


class Impl(Interface):

    def __init__(self, session):
        logger.info('********** impl is initial **********')
        self.lock = threading.Lock()
        self.s = session

    @exceptionWrapper
    def importTemplate(self, xml):
        '''importTemplate -- import XML into Portal's database
    Return Value
        Integer 0 - for successfully import
    Throws XmlImportError'''
        self.lock.acquire()
        try:
            import_xml(xml, self.s)
        finally:
            self.lock.release()

    def __do_template_header(self, iob):
        iob.write('%-13s %-36s %-18s %s' % ('ID', 'UUID', 'Name', 'Description'))

    def __do_template_list(self, iob, mapper):
        rset = self.s.query(mapper).order_by(mapper.id)
        for record in rset:
            key = '%s@%d' % (tableMapper2Key[mapper], record.id)
            uuid = string_trim(record.uuid, 36)
            name = string_trim(record.name, 18)
            description = string_trim(record.description)
            iob.write('%-13s %-36s %-18s %s' % (key, uuid, name, description))

    def __do_instance_header(self, iob):
        iob.write('%-13s %-36s %-18s %s' % ('ID', 'UUID', 'Name', 'Status'))

    # 获取某个类实例的方法调用
    def __try_getattr(self, obj, attr):
        try:
            return getattr(obj, attr)
        except:
            return 'No such field'

    def __do_instance_list(self, iob, mapper):
        rset = self.s.query(mapper).order_by(mapper.id)
        for record in rset:
            key = '%s@%d' % (tableMapper2Key[mapper], record.id)
            uuid = string_trim(self.__try_getattr(record, 'uuid'), 36)
            name = string_trim(self.__try_getattr(record, 'name'), 18)
            status = self.__try_getattr(record, 'status')
            iob.write('%-13s %-36s %-18s %s' % (key, uuid, name, status))

    def __do_job_header(self, iob):
        iob.write('%-3s %-36s %-18s %s' % ('ID', 'UUID', 'Title', 'Status'))

    def __do_job_list(self, iob, mapper):
        rset = self.s.query(mapper).order_by(mapper.id)
        for record in rset:
            id = record.id
            uuid = string_trim(record.uuid, 36)
            name = record.title
            status = record.status
            iob.write('%-3s %-36s %-18s %s' % (id, uuid, name, status))

    # 返回vcluster、vlab、vtemplate格式化模板列表
    @exceptionWrapper
    def listTemplate(self):
        self.lock.acquire()
        try:
            iob = StringIO()
            self.__do_template_header(iob)
            for mapper in templateMappers:
                self.__do_template_list(iob, mapper)
            return iob.getvalue()
        finally:
            self.lock.release()

    # 返回vcluster/vlab/vtemplate的uuid和name的字典
    @exceptionWrapper
    def listTemplateByType(self, typ):
        mapper = templateKey2Mapper[typ]
        self.lock.acquire()
        try:
            rset = self.s.query(mapper).order_by(mapper.id)
            dict = {}
            for record in rset:
                dict[record.uuid] = record.name
            return str(dict)
        finally:
            self.lock.release()

    def listVmTemp(self):
        self.lock.acquire()
        try:
            rset = self.s.query(VmTemp).order_by(VmTemp.id)
            dict = {}
            for record in rset:
                dict[record.uuid] = record.name
            return str(dict)
        finally:
            self.lock.release()

    #############################################################        

    # 获取虚拟机创建时间
    def getVmCreateTime(self, uuid):
        self.lock.acquire()
        try:
            vm = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == uuid)[0]
            return str(vm.created_at)
        finally:
            self.lock.release()

    # 获取虚拟机更新时间
    def getVmRecentStartTime(self, uuid):
        self.lock.acquire()
        try:
            vm = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == uuid)[0]
            return str(vm.updated_at)
        finally:
            self.lock.release()

    @exceptionWrapper
    def showTemplate(self, uuid):
        self.lock.acquire()
        try:
            obj = TemplateGetter.by_uuid(uuid, self.s)
            return export_xml(obj, self.s)
        finally:
            self.lock.release()

    @exceptionWrapper
    def showInstance(self, uuid):
        self.lock.acquire()
        try:
            obj = InstanceGetter.by_uuid(uuid, self.s)
            return export_xml(obj, self.s)
        finally:
            self.lock.release()

    @exceptionWrapper
    def showTemplateByKey(self, key):
        self.lock.acquire()
        try:
            obj = TemplateGetter.by_key(key, self.s)
            return export_xml(obj, self.s)
        finally:
            self.lock.release()

    # 删除满足uuid第一个记录模板
    @exceptionWrapper
    def removeTemplate(self, uuid):
        self.lock.acquire()
        try:
            obj = TemplateGetter.by_uuid(uuid, self.s)
            return remove_template(obj, self.s)
        finally:
            self.lock.release()
            self.s.close()

    # 删除满足uuid所有记录模板
    @exceptionWrapper
    def removeTemplates(self, uuid):
        self.lock.acquire()
        try:
            objs = TemplateGetter.by_key(uuid, self.s)
            for obj in objs:
                remove_template(obj, self.s)
        finally:
            self.lock.release()
            self.s.close()

    # 删除执行对象的模板
    @exceptionWrapper
    def removeTemplateByKey(self, key):
        self.lock.acquire()
        try:
            obj = TemplateGetter.by_key(key, self.s)
            return remove_template(obj, self.s)
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def listInstance(self):
        self.lock.acquire()
        try:
            iob = StringIO()
            self.__do_instance_header(iob)
            for mapper in instanceMappers:
                self.__do_instance_list(iob, mapper)
            return iob.getvalue()
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def listInstanceByType(self, typ):
        self.lock.acquire()
        try:
            mapper = instanceKey2Mapper[typ]
            iob = StringIO()
            self.__do_instance_header(iob)
            self.__do_instance_list(iob, mapper)
            return iob.getvalue()
        finally:
            self.lock.release()
            self.s.close()

    # 返回job的格式化信息列表
    @exceptionWrapper
    def listJob(self):
        iob = StringIO()
        self.__do_job_header(iob)
        self.__do_job_list(iob, Job)
        self.lock.release()
        return iob.getvalue()

    # 返回task的格式化信息列表
    @exceptionWrapper
    def listTask(self):
        iob = StringIO()
        self.__do_job_header(iob)
        self.__do_job_list(iob, Task)
        self.lock.release()
        return iob.getvalue()

    # 删除满足uuid的第一个记录
    @exceptionWrapper
    def removeInstance(self, uuid):
        self.lock.acquire()
        try:
            obj = InstanceGetter.by_uuid(uuid, self.s)
            return remove_instance(obj, self.s)
        finally:
            self.lock.release()
            self.s.close()

    # 删除满足uuid的所有记录
    @exceptionWrapper
    def removeInstances(self, uuid):
        self.lock.acquire()
        try:
            objs = InstanceGetter.by_uuids(uuid, self.s)
            for obj in objs:
                remove_instance(obj, self.s)
        finally:
            self.lock.release()
            self.s.close()

    # 根据主键删除一个记录
    @exceptionWrapper
    def removeInstanceByKey(self, key):
        self.lock.acquire()
        try:
            obj = InstanceGetter.by_key(key, self.s)
            return remove_instance(obj, self.s)
        finally:
            self.lock.release()
            self.s.close()

    # 生成一条job信息
    def __generate_job(self, instance, optype, title=None):
        logger.info('***** __generate_job is running *****')
        jobMapper2Key = {VirtualClusterInstance: 'vcluster', VlabInstance: 'vlab', VirtualMachineInstance: 'vmi',
                         VmTemp: 'vmt'}
        try:
            instance_type = jobMapper2Key[type(instance)]
            job = Job()
            job.uuid = GenUUID()
            if hasattr(instance, 'owner_id'):
                job.user_id = instance.owner_id
            job.title = title
            job.content = 'id:%d' % instance.id
            job.description = '%s %s %s' % (optype, instance_type, job.content)
            job.title = job.description  # '%s %s %s' % (optype, instance_type, instance.name)
            job.job_type = '%s_%s' % (instance_type, optype)
            job.status = 'pending'
            self.s.add(job)
            self.s.commit()
            return job
        except Exception as e:
            logger.info(e)
            return None

    # 根据模板创建虚拟机
    @exceptionWrapper
    def deployV(self, template_uuid, param2dict, ip_pool_id):
        logger.info('***** deployV is running *****')
        self.lock.acquire()
        try:
            logger.info('param vmc uuid: %s, temp uuid: %s' % (param2dict['hostId'], template_uuid))
            # 模板
            temp = self.s.query(VmTemp).filter(VmTemp.uuid == template_uuid)[0]
            #            #模板的原始虚拟机
            #            temp_vmi = self.s.query(VirtualMachineInstance).get(temp.ref_vmi_id)
            # 物理主机
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.uuid == param2dict['hostId'])[0]
            if param2dict.has_key('clusterId'):
                cluster = self.s.query(PhysicalCluster).filter(PhysicalCluster.uuid == param2dict['clusterId'])[0]
            else:
                cluster = self.s.query(PhysicalCluster).get(vmc.cluster_id)
            # 磁盘存储
            storage = self.s.query(Storage).filter(Storage.uuid == param2dict['datastoreId'])[0]
            # 登陆用户
            user = self.s.query(User).get(cluster.owner_id)
            # ip池
            ip_pool = self.s.query(IpPool).get(ip_pool_id)
            ips = [self.get_ip(ip_pool) for i in range(temp.nic_cnt)]
            logger.info('ips: %s' % ips)

            vmi = VirtualMachineInstance()
            vmi.uuid = GenUUID()
            vmi.hostname = param2dict['vmName']
            vmi.owner_id = cluster.owner_id
            vmi.mem_total = temp.memory
            vmi.disk_total = temp.disk
            vmi.cpu_cnt = temp.kind
            vmi.nic_cnt = temp.nic_cnt
            vmi.vm_temp_id = temp.id
            vmi.virtual_machine_container_id = vmc.id
            vmi.status = 'new'
            vmi.description = param2dict['annotation']
            vmi.cluster_id = cluster.id
            vmi.ip = ' '.join(ips)
            vmi.storage_id = storage.id
            vmi.temp_file_name = temp.name
            vmi.store_name = temp.url
            vmi.oper_system_name = temp.os_type
            vmi.oper_system_vendor_name = temp.distribution
            vmi.reserved = ip_pool.vlan

            nic_settings = []
            for ip in ips:
                nic_settings.append("<NIC>\
                <Address>%s</Address>\
                <MAC>%s</MAC>\
                <Netmask>%s</Netmask>\
                <Gateway>%s</Gateway>\
                <DNS>%s</DNS>\
                </NIC>" % (ip,
                           self.random_mac(),
                           ip_pool.netmask,
                           ip_pool.gateway,
                           ip_pool.dns))

            settings = "<vNode>\
            <Uuid>%s</Uuid>\
            <Type>Template</Type>\
            <Hostname>%s</Hostname>\
            <Desc> </Desc>\
            <CpuCnt>%s</CpuCnt>\
            <Mem>%s</Mem>\
            <Vlan>%s</Vlan>\
            <NicCnt>%s</NicCnt>\
            <DiskSize>%sg</DiskSize>\
            <VstoreIp>%s</VstoreIp>\
            <VstorePath>%s</VstorePath>\
            <OsType>%s</OsType>\
            <OsVersion>%s</OsVersion>\
            <vTemplateRef>%s</vTemplateRef>\
            <IsoPath>NON</IsoPath>\
            %s\
            <Password>%s</Password>\
            </vNode>" % (
                vmi.uuid,
                vmi.hostname,
                vmi.cpu_cnt,
                vmi.mem_total,
                int(vmi.reserved) - 1,
                vmi.nic_cnt,
                vmi.disk_total,
                storage.ip_address,
                storage.storage_path,
                vmi.oper_system_name,
                vmi.oper_system_vendor_name,
                vmi.store_name,
                '\n'.join(nic_settings),
                user.password)

            logger.info('deploy settings: %s' % settings)
            vmi.settings = settings
            self.s.add(vmi)
            self.s.commit()

            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_deploy'
            job.status = 'pending'
            job.title = 'Deploy virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Deploy virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error('deployV is error: %s' % e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    # 根据iso创建虚拟机
    @exceptionWrapper
    def createV(self, vmi_uuid, param2dict):
        logger.info('***** createV is running *****')
        self.lock.acquire()
        try:
            logger.info('param vmc uuid: %s' % param2dict['hostId'])
            # 物理主机
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.uuid == param2dict['hostId'])[0]
            # 集群
            if param2dict.has_key('clusterId'):
                cluster = self.s.query(PhysicalCluster).filter(PhysicalCluster.uuid == param2dict['clusterId'])[0]
            else:
                cluster = self.s.query(PhysicalCluster).get(vmc.cluster_id)
            # 磁盘存储
            storage = self.s.query(Storage).filter(Storage.uuid == param2dict['datastoreId'])[0]
            # 登陆用户
            user = self.s.query(User).get(cluster.owner_id)
            # ip池
            ip_pool = self.s.query(IpPool).get(param2dict['ipPoolId'])
            ips = [self.get_ip(ip_pool) for i in range(int(param2dict['nicCnt']))]
            logger.info('ips: %s, iso value is: %s' % (ips, param2dict['iso']))

            vmi = VirtualMachineInstance()
            vmi.uuid = GenUUID()
            vmi.hostname = param2dict['vmName']
            vmi.owner_id = cluster.owner_id
            vmi.mem_total = param2dict['memoryMB']
            vmi.disk_total = int(param2dict['diskTotal'])
            vmi.cpu_cnt = param2dict['numCPUs']
            vmi.nic_cnt = param2dict['nicCnt']
            vmi.virtual_machine_container_id = vmc.id
            vmi.status = 'new'
            vmi.description = param2dict['annotation']
            vmi.cluster_id = cluster.id
            vmi.ip = ' '.join(ips)
            vmi.storage_id = storage.id
            vmi.store_type = param2dict['iso']
            vmi.oper_system_name = param2dict['guestType']
            logger.info('oper_system_name value is: %s' % vmi.oper_system_name)
            if vmi.oper_system_name == 'Windows':
                windows_versions = ('xp', '7', '2003', '2008')
                for version in windows_versions:
                    if version.lower() in param2dict['iso'].lower():
                        vmi.oper_system_vendor_name = version
                        break
            elif vmi.oper_system_name == 'Linux':
                linux_versions = ('Debian', 'Ubuntu', 'CentOS', 'Redhat', 'SuSE')
                for version in linux_versions:
                    if version.lower() in param2dict['iso'].lower():
                        vmi.oper_system_vendor_name = version
                        break

            if vmi.oper_system_vendor_name is None:
                logger.error('oper_system_vendor_name can\'t None')
                return None

            vmi.reserved = ip_pool.vlan

            nic_settings = []
            for ip in ips:
                nic_settings.append("<NIC>\
                <Address>%s</Address>\
                <MAC>%s</MAC>\
                <Netmask>%s</Netmask>\
                <Gateway>%s</Gateway>\
                <DNS>%s</DNS>\
                </NIC>" % (ip,
                           self.random_mac(),
                           ip_pool.netmask,
                           ip_pool.gateway,
                           ip_pool.dns))

            settings = "<vNode>\
            <Uuid>%s</Uuid>\
            <Type>Template</Type>\
            <Hostname>%s</Hostname>\
            <Desc> </Desc>\
            <CpuCnt>%s</CpuCnt>\
            <Mem>%s</Mem>\
            <Vlan>%s</Vlan>\
            <NicCnt>%s</NicCnt>\
            <DiskSize>%sg</DiskSize>\
            <VstoreIp>%s</VstoreIp>\
            <VstorePath>%s</VstorePath>\
            <OsType>%s</OsType>\
            <OsVersion>%s</OsVersion>\
            <vTemplateRef>NON</vTemplateRef>\
            <IsoPath>%s</IsoPath>\
            %s\
            <Password>%s</Password>\
            </vNode>" % (
                vmi.uuid,
                vmi.hostname,
                vmi.cpu_cnt,
                vmi.mem_total,
                int(vmi.reserved) - 1,
                vmi.nic_cnt,
                vmi.disk_total,
                storage.ip_address,
                storage.storage_path,
                vmi.oper_system_name,
                vmi.oper_system_vendor_name,
                vmi.store_type,
                '\n'.join(nic_settings),
                user.password)

            logger.info('create settings: %s' % settings)
            vmi.settings = settings
            self.s.add(vmi)
            self.s.commit()

            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_create'
            job.status = 'pending'
            job.title = 'Deploy virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Deploy virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error('createV is error: %s' % e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    # 通过uuid重新生成一个执行创建的job
    @exceptionWrapper
    def redeployV(self, uuid):
        logger.info('***** redeployV is running *****')
        self.lock.acquire()
        try:
            instance = InstanceGetter.by_uuid(uuid, self.s)
            job = self.__generate_job(instance, 'deploy')
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    # 通过uuid生成一个执行开启虚拟机的job
    @exceptionWrapper
    def startV(self, vmi_uuid):
        logger.info('***** startV is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_start'
            job.status = 'pending'
            job.title = 'Start virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Start virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    # 通过key生成一个执行开启虚拟机的job
    @exceptionWrapper
    def startVmiByKey(self, key):
        logger.info('***** startVmiByKey is running *****')
        self.lock.acquire()
        try:
            instance = InstanceGetter.by_key(key, self.s)
            job = self.__generate_job(instance, 'start', 'Start virtual machine')
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    # 通过uuid生成一个执行停止虚拟机的job
    @exceptionWrapper
    def stopV(self, vmi_uuid):
        logger.info('***** stopV is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_stop'
            job.status = 'pending'
            job.title = 'Stop virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Stop virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    # 通过key生成一个执行停止虚拟机的job
    @exceptionWrapper
    def stopVmiByKey(self, key):
        logger.info('***** stopVmiByKey is running *****')
        self.lock.acquire()
        try:
            instance = InstanceGetter.by_key(key, self.s)
            job = self.__generate_job(instance, 'stop', 'Stop virtual machine')
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def restartV(self, vmi_uuid):
        logger.info('***** restartV is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_restart'
            job.status = 'pending'
            job.title = 'Restart virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Restart virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def pauseV(self, vmi_uuid):
        logger.info('***** pauseV is running *****')
        self.lock.acquire()
        try:
            # instance = InstanceGetter.by_uuid(uuid, self.s)
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_pause'
            job.status = 'pending'
            job.title = 'Pause virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Pause virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def resumeV(self, vmi_uuid):
        logger.info('***** resumeV is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_resume'
            job.status = 'pending'
            job.title = 'Resume virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Resume virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def undeployV(self, vmi_uuid):
        logger.info('***** undeployV is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_undeploy'
            job.status = 'pending'
            job.title = 'Undeploy virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Undeploy virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def undeployVmiByKey(self, key):
        logger.info('***** undeployVmiByKey is running *****')
        self.lock.acquire()
        try:
            instance = InstanceGetter.by_key(key, self.s)
            job = self.__generate_job(instance, 'undeploy', 'Undeploy virtual machine')
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    def __update_vminfo(self, instance, config_xml):
        doc = minidom.parseString(instance.settings.encode("utf-8"))
        update_doc = minidom.parseString(config_xml.encode("utf-8"))
        cpu_cnt = update_doc.getElementsByTagName('CpuCnt')[0].firstChild.data.strip()
        if cpu_cnt != '-1':
            doc.getElementsByTagName('CpuCnt')[0].firstChild.data = cpu_cnt
            instance.cpu_cnt = cpu_cnt

        # 内存单位为MB
        mem_size = update_doc.getElementsByTagName('Mem')[0].firstChild.data.strip()
        if mem_size != '-1':
            mem_size = int(mem_size) * 1024
            doc.getElementsByTagName('Mem')[0].firstChild.data = mem_size
            instance.mem_total = mem_size

        #        nic_num = update_doc.getElementsByTagName('NicCnt')[0].firstChild.data.strip()
        #        if nic_num != '-1':
        #            doc.getElementsByTagName('NicCnt')[0].firstChild.data = nic_num
        #            instance.nic_cnt = nic_num

        # 磁盘单位为GB
        disk_size = update_doc.getElementsByTagName('DiskSize')[0].firstChild.data.strip()
        if disk_size != '-1':
            doc.getElementsByTagName('DiskSize')[0].firstChild.data = '%sg' % (
                        int(disk_size) - int(instance.disk_total))
            instance.disk_total = disk_size

        instance.settings = doc.toxml()
        self.s.commit()

    @exceptionWrapper
    def reconfig(self, vmi_uuid, config_xml):
        logger.info('***** reconfig is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            self.__update_vminfo(vmi, config_xml)
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_config'
            job.status = 'pending'
            job.title = 'Change virtual machine'
            job.content = 'id:%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            job.description = "Change virtual machine id :%s" % vmi.id
            self.s.add(job)
            self.s.commit()
            return job.uuid
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def rename(self, vmi_uuid, name):
        logger.info('***** rename is running *****')
        self.lock.acquire()
        try:
            check_vmis = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.hostname == name)
            logger.info(dir(check_vmis))
            if check_vmis.count() == 0:
                instance = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)
                instance.hostname = name
                self.s.commit()
                return 1
            else:
                return 0
        finally:
            self.lock.release()
            self.s.close()

    # 基于虚机生成模板
    def createTempByParam(self, temp_name, storage_uuid, vmi_uuid):
        logger.info('***** Impl.py  createTempByParam is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            storage = self.s.query(Storage).filter(Storage.uuid == storage_uuid)[0]
            physical_cluster = self.s.query(PhysicalCluster).get(vmi.cluster_id)
            temp = VmTemp()
            temp.uuid = GenUUID()
            temp.name = temp_name
            temp.status = 'new'
            temp.deploy_url = 'nfs://%s%s/nfsbase/%s.img' % (storage.ip_address, storage.storage_path, temp.uuid)
            temp.os_type = vmi.oper_system_name
            temp.distribution = vmi.oper_system_vendor_name
            temp.memory = vmi.mem_total
            temp.disk = vmi.disk_total
            temp.kind = vmi.cpu_cnt
            temp.deploy_cowdir = "nfs://%s%s/nfscow" % (storage.ip_address, storage.storage_path)
            temp.url = "http://%s:8080/vstore/template/%s.xml" % (storage.ip_address, temp.uuid)
            temp.datacenter_id = physical_cluster.datacenter_id
            temp.ref_vmi_id = vmi.id
            temp.nic_cnt = vmi.nic_cnt

            temp.prefer_settings = "<vNode>\
                <VmiUuid>%s</VmiUuid>\
                <TempUuid>%s</TempUuid>\
                <TempName>%s</TempName>\
                <Desc>NONE</Desc>\
                <OsType>%s</OsType>\
                <MemSize>%s</MemSize>\
                <DiskSize>%s</DiskSize>\
                <VstorePath>%s</VstorePath>\
                <IsoPath>None</IsoPath>\
                <VmiType>%s</VmiType>\
                </vNode>" % (vmi.uuid,
                             temp.uuid,
                             temp.name,
                             temp.os_type,
                             temp.memory,
                             temp.disk,
                             '%s:%s' % (storage.ip_address, storage.storage_path),
                             vmi.storeid)

            logger.info('settings: %s' % temp.prefer_settings)
            self.s.add(temp)
            self.s.commit()

            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmt_create'
            job.status = 'pending'
            job.title = 'Create template'
            job.content = 'id:%s' % temp.id
            job.datacenter_id = temp.datacenter_id
            job.ref_obj_id = temp.id
            job.ref_obj_name = temp.name
            job.ref_obj_type = 4
            job.description = "Create template"
            self.s.add(job)
            self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error(e.message)
            return 0
        finally:
            self.lock.release()
            self.s.close()

    def get_ip(self, ip_pool):
        logger.info('***** Impl.py get_ip is running *****')
        try:
            logger.info('ip_pool_id: %s' % ip_pool.id)
            if ip_pool is None or ip_pool.out_of_usage == 1:
                return '127.0.0.1'
            ips = self.s.query(Ip).filter(and_(Ip.ip_pool_id == ip_pool.id, Ip.status == 0))
            if ips is None or ips.count() == 0:
                ip_pool.out_of_usage = 1
                return '127.0.0.1'
            else:
                ips[0].status = 1
            self.s.commit()
            return ips[0].ip
        except Exception as e:
            logger.error('get_ip is error: %s' % e.message)
            return '127.0.0.1'

    def random_mac(self):
        logger.info('***** Impl.py random_mac is running *****')
        hexList = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"]
        res = "52:54:00"
        for i in range(3):
            res += ":%s%s" % (
            hexList[random.randint(0, len(hexList) - 1)], hexList[random.randint(0, len(hexList) - 1)])
        logger.info('mac vlaue: %s' % res)
        return res

    # 克隆虚机
    def cloneVm(self, clone_vm_name, vmi_uuid):
        logger.info('***** Impl.py  cloneVm is running *****')
        self.lock.acquire()
        try:
            original_vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            original_storage = self.s.query(Storage).get(original_vmi.storage_id)

            clone_vmi = VirtualMachineInstance()
            clone_vmi.uuid = GenUUID()
            clone_vmi.hostname = clone_vm_name
            clone_vmi.virtual_machine_container_id = original_vmi.virtual_machine_container_id
            clone_vmi.status = 'new'
            clone_vmi.description = original_vmi.description
            clone_vmi.cpu_cnt = original_vmi.cpu_cnt
            clone_vmi.mem_total = original_vmi.mem_total
            clone_vmi.reserved = original_vmi.reserved
            clone_vmi.nic_cnt = original_vmi.nic_cnt
            clone_vmi.disk_total = original_vmi.disk_total
            clone_vmi.store_name = original_vmi.store_name
            clone_vmi.oper_system_name = original_vmi.oper_system_name
            clone_vmi.oper_system_vendor_name = original_vmi.oper_system_vendor_name
            clone_vmi.storeid = original_vmi.storeid
            clone_vmi.store_type = original_vmi.store_type
            clone_vmi.cluster_id = original_vmi.cluster_id
            clone_vmi.storage_id = original_vmi.storage_id
            clone_vmi.owner_id = original_vmi.owner_id
            clone_vmi.vm_temp_id = original_vmi.vm_temp_id
            ip_pool = self.s.query(IpPool).filter(and_(IpPool.out_of_usage == 0, IpPool.vlan == clone_vmi.reserved))[0]
            user = self.s.query(User).get(clone_vmi.owner_id)
            ips = [self.get_ip(ip_pool) for i in range(clone_vmi.nic_cnt)]
            clone_vmi.ip = ' '.join(ips)

            nic_settings = []
            for ip in ips:
                nic_settings.append("<NIC>\
                <Address>%s</Address>\
                <MAC>%s</MAC>\
                <Netmask>%s</Netmask>\
                <Gateway>%s</Gateway>\
                <DNS>%s</DNS>\
                </NIC>" % (ip,
                           self.random_mac(),
                           ip_pool.netmask,
                           ip_pool.gateway,
                           ip_pool.dns))

            clone_vmi.settings = "<vNode>\
            <Uuid>%s</Uuid>\
            <Type>%s</Type>\
            <Hostname>%s</Hostname>\
            <Desc> </Desc>\
            <CpuCnt>%s</CpuCnt>\
            <Mem>%s</Mem>\
            <Vlan>%s</Vlan>\
            <NicCnt>%s</NicCnt>\
            <DiskSize>%sg</DiskSize>\
            <VstoreIp>%s</VstoreIp>\
            <VstorePath>%s</VstorePath>\
            <OsType>%s</OsType>\
            <OsVersion>%s</OsVersion>\
            <vTemplateRef>%s</vTemplateRef>\
            <IsoPath>%s</IsoPath>\
            %s\
            <Password>%s</Password>\
            </vNode>" % (clone_vmi.uuid,
                         clone_vmi.storeid,
                         clone_vm_name,
                         clone_vmi.cpu_cnt,
                         clone_vmi.mem_total,
                         int(clone_vmi.reserved) - 1,
                         clone_vmi.nic_cnt,
                         clone_vmi.disk_total,
                         original_storage.ip_address,
                         original_storage.storage_path,
                         clone_vmi.oper_system_name,
                         clone_vmi.oper_system_vendor_name,
                         clone_vmi.storeid == 'Template' and clone_vmi.store_name or 'NON',
                         clone_vmi.storeid == 'Iso' and clone_vmi.store_type or 'NON',
                         '\n'.join(nic_settings),
                         user.password)

            logger.info(clone_vmi.settings)
            self.s.add(clone_vmi)
            self.s.commit()

            job = Job()
            job.uuid = GenUUID()
            job.user_id = original_vmi.owner_id
            job.job_type = 'vmi_clone'
            job.status = 'pending'
            job.title = 'Clone virtual machine'
            job.content = 'id:%s' % clone_vmi.id
            job.description = 'Clone virtual machine id :%s' % original_vmi.id
            job.cluster_id = original_vmi.cluster_id
            job.host_id = original_vmi.virtual_machine_container_id
            job.vm_id = original_vmi.id
            job.ref_obj_id = original_vmi.id
            job.ref_obj_name = original_vmi.hostname
            self.s.add(job)
            self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def migrateVm(self, vmi_uuid, remote_vmc_uuid):
        logger.info('***** Impl.py migrateVm is running *****')
        self.lock.acquire()
        try:
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.uuid == remote_vmc_uuid)[0]
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            if vmi.status != "running" and vmi.status != "stopped":
                logger.error('vmi status: %s' % vmi.status)
                return None

            if vmi.virtual_machine_container_id == vmc.id:
                logger.error(
                    'remote_vmc_id: %s, virtual_machine_container_id: %s' % (vmc.id, vmi.virtual_machine_container_id))
                return None

            if vmi.status == 'running':
                vmi_status = 'vmotioning'
                job_type = 'vmi_vmotion'
            else:
                vmi_status = 'migrating'
                job_type = 'vmi_migrate'

            vmi.mig_info = vmi.status
            vmi.status = vmi_status
            vmi.target_vmc_id = vmc.id
            self.s.commit()

            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = job_type
            job.status = 'pending'
            job.title = 'Migrate virtual machine'
            job.content = 'id:%s' % vmi.id
            job.description = 'Mirgrate virtual machine id :%s' % vmi.id
            job.cluster_id = vmi.cluster_id
            job.host_id = vmi.virtual_machine_container_id
            job.vm_id = vmi.id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            self.s.add(job)
            self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def createSnapshotVm(self, vmi_uuid, snapshot_name, snapshot_description):
        logger.info('***** Impl.py createSnapshotVm is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            snapshot = Snapshot()
            snapshot.uuid = GenUUID()
            snapshot.vm_id = vmi.id
            snapshot.name = snapshot_name
            snapshot.description = snapshot_description
            snapshot.user_id = vmi.owner_id
            self.s.add(snapshot)
            self.s.commit()

            vmi.mig_info = vmi.status
            vmi.snapshot_id = snapshot.id
            self.s.commit()

            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_createsnapshot'
            job.status = 'pending'
            job.title = 'Create snapshot'
            job.description = 'Create snapshot for vm id :%s' % vmi.id
            job.content = 'id:%s,snapshot:%s' % (vmi.id, snapshot.name)
            job.cluster_id = vmi.cluster_id
            job.host_id = vmi.virtual_machine_container_id
            job.vm_id = vmi.id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            self.s.add(job)
            self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def rollbackVmById(self, vmi_uuid, snapshot_uuid):
        logger.info('***** Impl.py rollbackVmById is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            vmi.mig_info = vmi.status

            snapshot = self.s.query(Snapshot).filter(Snapshot.uuid == snapshot_uuid)[0]

            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_rollback'
            job.status = 'pending'
            job.title = 'Rollback vm'
            job.description = 'Rollback virtual machine id :%s' % vmi.id
            job.content = 'id:%s,snapshot:%s' % (vmi.id, snapshot.name)
            job.cluster_id = vmi.cluster_id
            job.host_id = vmi.virtual_machine_container_id
            job.vm_id = vmi.id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            self.s.add(job)
            self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def renameSnapshot(self, old_snapshot_uuid, new_snapshot_name, description):
        logger.info('***** Impl.py renameSnapshot is running *****')
        self.lock.acquire()
        try:
            snapshot = self.s.query(Snapshot).filter(Snapshot.uuid == old_snapshot_uuid)[0]
            snapshot.description = description
            self.s.commit()
            return '1'
        except Exception as e:
            logger.error(e.message)
            return '0'
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def removeSnapshotById(self, vmi_uuid, snapshot_uuid, is_remove_child):
        logger.info('***** Impl.py removeSnapshotById is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            snapshot = self.s.query(Snapshot).filter(Snapshot.uuid == snapshot_uuid)[0]
            self.s.delete(snapshot)
            job = Job()
            job.uuid = GenUUID()
            job.user_id = vmi.owner_id
            job.job_type = 'vmi_deletesnapshot'
            job.status = 'pending'
            job.title = 'Delete snapshot'
            job.description = 'Delete snapshot for vm id :%s' % vmi.id
            job.content = 'id:%s,snapshot:%s' % (vmi.id, snapshot.name)
            job.cluster_id = vmi.cluster_id
            job.host_id = vmi.virtual_machine_container_id
            job.vm_id = vmi.id
            job.ref_obj_id = vmi.id
            job.ref_obj_name = vmi.hostname
            self.s.add(job)
            self.s.commit()
            while is_remove_child and snapshot.depend_snapshot_id is not None:
                snapshot = self.s.query(Snapshot).get(snapshot.depend_snapshot_id)
                self.s.delete(snapshot)
                job = Job()
                job.uuid = GenUUID()
                job.user_id = vmi.owner_id
                job.job_type = 'vmi_deletesnapshot'
                job.status = 'pending'
                job.title = 'Delete snapshot'
                job.description = 'Delete snapshot for vm id :%s' % vmi.id
                job.content = 'id:%s,snapshot:%s' % (vmi.id, snapshot.name)
                job.cluster_id = vmi.cluster_id
                job.host_id = vmi.virtual_machine_container_id
                job.vm_id = vmi.id
                job.ref_obj_id = vmi.id
                job.ref_obj_name = vmi.hostname
                self.s.add(job)
                self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def removeAllSnapshot(self, vmi_uuid):
        logger.info('***** Impl.py removeSnapshotByName is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            snapshots = self.s.query(Snapshot).filter(Snapshot.vm_id == vmi.id)
            for snapshot in snapshots:
                self.s.delete(snapshot)

                job = Job()
                job.uuid = GenUUID()
                job.user_id = vmi.owner_id
                job.job_type = 'vmi_deletesnapshot'
                job.status = 'pending'
                job.title = 'Delete snapshot'
                job.description = 'Delete snapshot for vm id :%s' % vmi.id
                job.content = 'id:%s,snapshot:%s' % (vmi.id, snapshot.name)
                job.cluster_id = vmi.cluster_id
                job.host_id = vmi.virtual_machine_container_id
                job.vm_id = vmi.id
                job.ref_obj_id = vmi.id
                job.ref_obj_name = vmi.hostname
                self.s.add(job)
                self.s.commit()
            return job.uuid
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getSnapshotsByVmiId(self, vmi_uuid):
        logger.info('***** Impl.py getSnapshotsByVmiId is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            snapshots = self.s.query(Snapshot).filter(Snapshot.vm_id == vmi.id)
            return list(snapshots)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getSnapshotsByVmiUuid(self, vmi_uuid):
        logger.info('***** Impl.py getSnapshotsByVmiUuid is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            snapshots = self.s.query(Snapshot).filter(Snapshot.vm_id == vmi.id)
            return list(snapshots)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAllHost(self):
        logger.info('***** Impl.py getAllHost is running *****')
        self.lock.acquire()
        try:
            vmcs = self.s.query(VirtualMachineContainer).order_by(VirtualMachineContainer.id)
            list_vmcs = list(vmcs)
            return list_vmcs
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    def getHostByUuid(self, vmc_uuid):
        logger.info('***** Impl.py getHostByUuid is running *****')
        self.lock.acquire()
        try:
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.uuid == vmc_uuid)[0]
            return vmc
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getHostByName(self, host_name):
        logger.info('***** Impl.py getHostByName is running *****')
        self.lock.acquire()
        try:
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.hostname == host_name)[0]
            return vmc
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getHostsByClusterId(self, cluster_id):
        logger.info('***** Impl.py getHostsByClusterId is running *****')
        self.lock.acquire()
        try:
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.cluster_id == cluster_id)
            list_vmc = list(vmc)
            return list_vmc
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getHostsByClusterUuid(self, cluster_uuid):
        logger.info('***** Impl.py getHostsByClusterUuid is running *****')
        self.lock.acquire()
        try:
            cluster = self.s.query(PhysicalCluster).filter(PhysicalCluster.uuid == cluster_uuid)[0]
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.cluster_id == cluster.id)
            list_vmc = list(vmc)
            return list_vmc
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getHostsByClusterName(self, cluster_name):
        logger.info('***** Impl.py getHostsByClusterName is running *****')
        self.lock.acquire()
        try:
            cluster = self.s.query(PhysicalCluster).filter(PhysicalCluster.name == cluster_name)[0]
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.cluster_id == cluster.id)
            list_vmc = list(vmc)
            return list_vmc
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getClustersByDatacenterId(self, datacenter_id):
        logger.info('***** Impl.py getClustersByDatacenterId is running *****')
        self.lock.acquire()
        try:
            clusters = self.s.query(PhysicalCluster).filter(PhysicalCluster.datacenter_id == datacenter_id)
            list_clusters = list(clusters)
            return list_clusters
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getClustersByDatacenterUuid(self, datacenter_uuid):
        logger.info('***** Impl.py getClustersByDatacenterUuid is running *****')
        self.lock.acquire()
        try:
            datacenter = self.s.query(Datacenter).filter(Datacenter.uuid == datacenter_uuid)[0]
            clusters = self.s.query(PhysicalCluster).filter(PhysicalCluster.datacenter_id == datacenter.id)
            list_clusters = list(clusters)
            return list_clusters
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getHostsByDatacenterUuid(self, datacenter_uuid):
        logger.info('***** Impl.py getHostsByDatacenterUuid is running *****')
        self.lock.acquire()
        try:
            datacenter = self.s.query(Datacenter).filter(Datacenter.uuid == datacenter_uuid)[0]
            hosts = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.datacenter_id == datacenter.id)
            list_hosts = list(hosts)
            return list_hosts
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getDatacenters(self):
        logger.info('***** Impl.py getDatacenters is running *****')
        self.lock.acquire()
        try:
            datacenters = self.s.query(Datacenter).all()
            logger.info(datacenters)
            list_datacenters = list(datacenters)
            return list_datacenters
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAllTemplates(self):
        logger.info('***** Impl.py getAllTemplates is running *****')
        self.lock.acquire()
        try:
            templates = self.s.query(VmTemp).all()
            return templates
        except Exception as e:
            logger.error('getAllTemplates is error: %s' % e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAllVmis(self):
        logger.info('***** Impl.py getAllVmis is running *****')
        self.lock.acquire()
        try:
            vmis = self.s.query(VirtualMachineInstance).all()
            return list(vmis)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getVHostById(self, vmi_id):
        logger.info('***** Impl.py getVHostById is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).get(vmi_id)
            return vmi
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getVHostByUuid(self, vmi_uuid):
        logger.info('***** Impl.py getVHostByUuid is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            return vmi
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getVHostByName(self, hostname):
        logger.info('***** Impl.py getVHostByName is running *****')
        self.lock.acquire()
        try:
            vmis = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.hostname == hostname)
            return list(vmis)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getVmisByHostId(self, host_id):
        logger.info('***** Impl.py getVmisByHostId is running *****')
        self.lock.acquire()
        try:
            vmis = self.s.query(VirtualMachineInstance).filter(
                VirtualMachineInstance.virtual_machine_container_id == host_id)
            list_vmis = list(vmis)
            return list_vmis
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getVmisByHostUuid(self, host_uuid):
        logger.info('***** Impl.py getVmisByHostUuid is running *****')
        self.lock.acquire()
        try:
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.uuid == host_uuid)[0]
            vmis = self.s.query(VirtualMachineInstance).filter(
                VirtualMachineInstance.virtual_machine_container_id == vmc.id)
            list_vmis = list(vmis)
            return list_vmis
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getJobById(self, job_uuid):
        logger.info('***** Impl.py getJobById is running *****')
        self.lock.acquire()
        try:
            job = self.s.query(Job).filter(Job.uuid == job_uuid)[0]
            return job
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def removeTemplateByVmiId(self, temp_id):
        logger.info('***** Impl.py removeTemplateByVmiId is running *****')
        self.lock.acquire()
        try:
            temp = self.s.query(VmTemp).get(temp_id)
            vmis = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.vm_temp_id == temp.id)
            # 只有该模板没有被用的情况下才允许被删除
            if vmis.count() == 0:
                self.s.delete(temp)
                self.s.commit()
                return 1
            else:
                return 0
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def removeTemplateByVmiUuid(self, temp_uuid):
        logger.info('***** Impl.py removeTemplateByVmiUuid is running *****')
        self.lock.acquire()
        try:
            temp = self.s.query(VmTemp).filter(VmTemp.uuid == temp_uuid)[0]
            vmis = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.vm_temp_id == temp.id)
            # 只有该模板没有被用的情况下才允许被删除
            if vmis.count() == 0:
                self.s.delete(temp)
                self.s.commit()
                return 1
            else:
                return 0
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAllAlarms(self):
        logger.info('***** Impl.py getAllAlarms is running *****')
        self.lock.acquire()
        try:
            alarms = self.s.query(Alarm).all()
            return list(alarms)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAlarmsByObjId(self, vmc_uuid):
        logger.info('***** Impl.py getAlarmById is running *****')
        self.lock.acquire()
        try:
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.uuid == vmc_uuid)[0]
            alarms = self.s.query(Alarm).filter(Alarm.ref_obj_id == vmc.id)
            return list(alarms)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAlarmsByObjIdAndName(self, vmc_uuid, ref_obj_name):
        logger.info('***** Impl.py getAlarmsByObjIdAndName is running *****')
        self.lock.acquire()
        try:
            vmc = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.uuid == vmc_uuid)[0]
            alarms = self.s.query(Alarm).filter(and_(Alarm.ref_obj_id == vmc.id, Alarm.ref_obj_name == ref_obj_name))
            return list(alarms)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAllStorages(self):
        logger.info('***** Impl.py getAllStorages is running *****')
        self.lock.acquire()
        try:
            storages = self.s.query(Storage).all()
            return list(storages)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getStorageById(self, storage_uuid):
        logger.info('***** Impl.py getStorageById is running *****')
        self.lock.acquire()
        try:
            storage = self.s.query(Storage).filter(Storage.uuid == storage_uuid)[0]
            return storage
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getIsoPath(self, storage_uuid):
        logger.info('***** Impl.py getIsoPath is running *****')
        self.lock.acquire()
        try:
            storage = self.s.query(Storage).filter(Storage.uuid == storage_uuid)[0]
            return storage.storage_path
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getIsoList(self, storage_uuid):
        logger.info('***** Impl.py getIsoList is running *****')
        self.lock.acquire()
        try:
            storage = self.s.query(Storage).filter(Storage.uuid == storage_uuid)[0]
            local_ips = \
            commands.getstatusoutput("/sbin/ifconfig | sed -n '/inet/'p |awk '{print $2}'|awk -F':' '{print $2}'")[
                1].split()
            if storage.ip_address.strip() in local_ips:
                isos = commands.getstatusoutput(
                    "ls -l %s |grep ^-|awk '{print $NF}'|egrep 'iso|nrg|img'" % storage.storage_path)[1].split()
            else:
                spawn_cmd = 'ssh %s@%s' % (storage.user_name, storage.ip_address)
                logger.info(spawn_cmd)
                ssh_conn = pexpect.spawn(spawn_cmd)
                ssh_conn.expect(
                    ['Are you sure you want to continue connecting (yes/no)?', pexpect.EOF, pexpect.TIMEOUT],
                    timeout=30)
                ssh_conn.sendline('yes')
                ssh_conn.expect(['password:', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
                ssh_conn.sendline(storage.password)
                isos = commands.getstatusoutput(
                    "ls -l %s |grep ^-|awk '{print $NF}'|egrep 'iso|nrg|img'" % storage.storage_path)[1].split()
                ssh_conn.sendline('exit')
                ssh_conn.eof()
                ssh_conn.close()
            return isos
        except BaseException, e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getVmiPowerState(self, vmi_uuid):
        logger.info('***** Impl.py getVmiPowerState is running *****')
        self.lock.acquire()
        try:
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.uuid == vmi_uuid)[0]
            #            job = Job()
            #            job.uuid = GenUUID()
            #            job.job_type = 'vmi_check'
            #            job.status = 'pending'
            #            job.title = 'Check vm'
            #            job.user_id = vmi.owner_id
            #            job.description = 'Check virtual machine id :%s' % vmi.id
            #            job.content = 'id:%s' % vmi.id
            #            job.cluster_id = vmi.cluster_id
            #            job.host_id = vmi.virtual_machine_container_id
            #            job.vm_id = vmi.id
            #            job.ref_obj_id = vmi.id
            #            job.ref_obj_name = vmi.hostname
            #            self.s.add(job)
            #            self.s.commit()
            return vmi.status, vmi.ip
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getAllIpPools(self):
        logger.info('***** Impl.py getAllIpPools is running *****')
        self.lock.acquire()
        try:
            vlans = self.s.query(IpPool).all()
            return list(vlans)
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def getUuidById(self, id, type):
        logger.info('***** Impl.py getUuidById is running *****')
        self.lock.acquire()
        try:
            if instanceKey2Mapper.has_key(type):
                instance = instanceKey2Mapper[type]
                uuid = self.s.query(instance).get(id).uuid
            else:
                return None
            return uuid
        except Exception as e:
            logger.error(e.message)
            return None
        finally:
            self.lock.release()
            self.s.close()

    @exceptionWrapper
    def update_ha_info(self, master_ip, cluster, info_dict):
        try:
            import datetime
            master_ip = eval(master_ip)
            cluster_id = int(eval(cluster))
            info_dict = eval(info_dict)
            logger.info('@update_ha_info(), master_ip: %s' % master_ip)
            logger.info('@update_ha_info(), info_dict: %s' % str(info_dict))

            # 更新ha节点数据
            ha_list = self.s.query(Ha).filter(Ha.vmc_ip == master_ip).all()
            if ha_list == []:  ##find a new master!##
                logger.info('@update_ha_info(), find a new master: %s' % master_ip)
                ha = Ha()
                ha.cluster_id = cluster_id
                ha.vmc_ip = master_ip
                ha.created_at = datetime.datetime.now()
                ha.updated_at = datetime.datetime.now()
                ha.status = 1  ###0:off, 1:live, 2:migrate, 3:succeed, 4:deleted###
                ha.times = 0
                self.s.add(ha)
                self.s.commit()
            elif len(info_dict) != 0:  ##update the master!##
                ha = ha_list[0]
                if ha.status != 4:
                    ha.updated_at = datetime.datetime.now()
                    ha.cluster_id = cluster_id
                    ha.status = 1
                    ha.times = 0
                    self.s.commit()

            for key in info_dict:
                ha_list = self.s.query(Ha).filter(Ha.vmc_ip == key[0]).all()
                if ha_list == []:  ##find a new slave!##
                    logger.info('@update_ha_info(), find a new slave: %s' % key[0])
                    ha = Ha()
                    ha.cluster_id = cluster_id
                    ha.vmc_ip = str(key[0])
                    ha.created_at = datetime.datetime.now()
                    ha.updated_at = datetime.datetime.now()
                    ha.status = 0 if info_dict[key] == 'N' else 1
                    ha.times = 0
                    self.s.add(ha)
                    self.s.commit()
                else:  ##update the slave!##
                    ha = ha_list[0]
                    if info_dict[key] == 'Y' and ha.status != 4:
                        ha.updated_at = datetime.datetime.now()
                        ha.cluster_id = cluster_id
                        ha.status = 1
                        ha.times = 0
                        self.s.commit()

            # 寻找ha单点，发起迁移操作
            ha_list = self.s.query(Ha).all()
            for ha in ha_list:
                if ha.status == 2 and ha.runtime:
                    job = self.s.query(Job).filter(Job.uuid == ha.runtime)[0]
                    if job.status == 'finished':
                        ha.status = 3
                        ha.times = 0
                    elif job.status == 'failed' and ha.times < 2:  # 重试2次
                        ha.times += 1
                        ha.status = 0
                    self.s.commit()

                if ha.status in (0, 1) and (datetime.datetime.now() - ha.updated_at).seconds > 10:  # 10 seconds!
                    # 迁移该主机上的虚拟机
                    tmp_list = self.s.query(Ha).filter(
                        and_(Ha.cluster_id == cluster_id, or_(Ha.status == 0, Ha.status == 1))).all()
                    if len(tmp_list) > 1:
                        vmc = \
                        self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.address == ha.vmc_ip)[0]
                        job = Job()  # 产生迁移虚拟机的工作任务
                        job.user_id = vmc.owner_id
                        job.uuid = GenUUID()
                        job.title = "Migrate host VMs"
                        job.description = "Migrate host VMs id:" + str(vmc.id)
                        job.job_type = 'vmc_hamigrate'  # 执行ha迁移
                        job.status = "pending"
                        job.content = "id:" + str(vmc.id)
                        job.cluster_id = vmc.cluster_id
                        job.host_id = vmc.id
                        job.ref_obj_id = vmc.id
                        job.ref_obj_name = vmc.hostname
                        logger.info('@generate_migrate_vmi_job(), new job -> %s' % job.uuid)
                        self.s.add(job)
                        self.s.commit()

                        ha.status = 2
                        ha.runtime = job.uuid  # 跟踪迁移任务
                        self.s.commit()
                        logger.info('@update_ha_info(), submit jobs of migrating VMs located in %s' % ha.vmc_ip)
                    else:
                        logger.info('@update_ha_info(), there is only one node in the cluster! -- %s' % ha.vmc_ip)
        except Exception, err:
            logger.error('@udpate_ha_info(), exception: %s' % str(err))


##for test##
if __name__ == '__main__':
    print('ok')
