# -*- coding: utf-8 -*-
import os
import random
import re
import socket
import threading
import time

import Queue
import urllib2
from SOAPpy import SOAPProxy
from sqlalchemy.sql.expression import and_, or_

from core import Logging, Config, project_path
from Utils import GenUUID
from ContainerOp import get_vmc_url, DummySOAPProxy
from Impl import InstanceGetter
from Model import *

logger = Logging.get_logger('hicloud.vsched.Controller')

# modify by cuilei, Sep 20th, 2011
failedTransTable = {
    'deploying': 'invalid',
    'starting': 'stopped',
    'stopping': 'running',
    'undeploying': 'stopped',
    'migrating': 'stopped',  # 冷迁移
    'vmotioning': 'running',  # 热迁移
    'scaling': 'running',
    'importing': 'invalid',
    'pausing': 'running',
    'resuming': 'paused',
    'snapshotting': 'running',
    'deletting': 'running',
    'rolling-back': 'running',
    'running': 'running',
    'cloning': 'invalid',
    'creating': 'invalid',
    'restarting': 'stopped',
    'configing': 'stopped',
    'starttemping': 'stopped',
    'invalid': 'invalid',
    'error': 'error',
    'adding': 'unknown',
    'updating': 'online',
    'stopped': 'stopped',
    'paused': 'paused',
    'unknown': 'unknown',
    'deleting': 'error',
    'checking': 'checked',
    'hastartting': 'normal',
    'hastopping': 'normal',
    'normal': 'normal',
    'updating': 'online'
}

finishedTransTable = {
    'deploying': 'stopped',
    'starting': 'running',
    'stopping': 'stopped',
    'undeploying': 'undeployinged',
    'undeployinged': 'undeployed',
    'migrating': 'stopped',  # 冷迁移
    'vmotioning': 'running',  # 热迁移
    'running': 'running',
    'scaling': 'running',
    'importing': 'running',
    'pausing': 'paused',
    'resuming': 'running',
    'snapshotting': 'running',
    'deletting': 'running',
    'rolling-back': 'running',
    # 'cloning': 'hibernated',
    'cloning': 'stopped',
    'configing': 'stopped',
    'creating': 'stopped',
    # it's awful to do this for single vm operation, but... ,modify by dy, change running to stopped
    'restarting': 'running',
    'starttemping': 'running',
    'stopped': 'stopped',
    'invalid': 'invalid',
    'paused': 'paused',
    'adding': 'online',
    'updating': 'online',
    'online': 'online',
    'deleting': 'deleted',
    'deleted': 'deleted',
    'checking': 'checked',
    'hastartting': 'normal',
    'hastopping': 'normal',
    'normal': 'normal',
    'updating': 'online'
}

stateOps = {
    'new': ['deploy', 'import', 'clone', 'create', 'add'],
    'stopped': ['start', 'undeploy', 'createt', 'clone', 'config', 'starttemp', 'createsnapshot', 'deletesnapshot',
                'rollback', 'check'],
    'undeploying': ['undeploy', 'delete'],
    'migrating': ['migrate'],
    'vmotioning': ['vmotion'],
    'running': ['stop', 'scale_more', 'scale_less', 'pause', 'snapshot', 'createsnapshot', 'deletesnapshot', 'rollback',
                'restart', 'check'],
    'paused': ['resume', 'undeploy', 'stop'],
    'error': ['undeploy', 'restart', 'stop'],
    'unknown': ['add'],
    'online': ['update'],
    'normal': ['hastart', 'hastop']
}

opToStates = {
    'import': 'importing',
    'deploy': 'deploying',
    'start': 'starting',
    'stop': 'stopping',
    'undeploy': 'undeploying',
    'migrate': 'migrating',  # 冷迁移
    'vmotion': 'vmotioning',  # 热迁移
    'scale_more': 'scaling',
    'scale_less': 'scaling',
    'pause': 'pausing',
    'resume': 'resuming',
    'snapshot': 'snapshotting',
    'createsnapshot': 'snapshotting',
    'deletesnapshot': 'deletting',
    'rollback': 'rolling-back',
    'clone': 'cloning',
    'createt': 'creating',
    'restart': 'restarting',
    'config': 'configing',
    'create': 'creating',
    'starttemp': 'starttemping',
    'add': 'adding',
    'update': 'updating',
    'delete': 'deleting',
    'check': 'checking',
    'hastart': 'hastartting',
    'hastop': 'hastopping'
}

resTransTable = {
    '0': 'success',
    '-1': 'saveFileErr',
    '-2': 'DownLoadcertErr',
    '-3': 'VSWConfNotExistErr',
    '-4': 'LibvirtOffErr',
    '-5': 'VPNConfNotExistErr',
    '-6': 'CreateNetXMLErr',
    '-7': 'IfconfigUPErr',
    '-8': 'VSwitchOffErr',
    '-9': 'IfconfigDownErr',
    '-10': 'OtherException',
    '-11': 'DestroyVSwitchErr',
    '-12': 'ParseConfErr',
    '-13': 'StartVSwitchErr',
    '-14': 'CreateVMErr',
    '-15': 'ShutdownVMErr',
    '-16': 'UUIDNullErr',
    '-17': 'DownloadRFSErr',
    '-18': 'CreateVMImgErr',
    '-19': 'VMImgNotExistErr',
    '-20': 'RemoveVMDirErr',
    '-21': 'VMCErr',
    '-22': 'DConnErr',
    '-23': 'DomainByUUIDNotFoundErr',
    '-24': 'MigFailErr',
    '-25': 'FileNotExistsErr',
    '-26': 'HibernateVMErr',
    '-27': 'ResumeVMErr',
    '-28': 'SnapShotVMErr',
    '-29': 'RollbackVMErr',
    '-30': 'CloneVMErr',
    '-33': 'DownloadDiskRefErr',
    '-34': 'DownloadMemRefErr',
}


class DummyObject:
    pass


class TaskRunner(threading.Thread):
    ''''TaskRunner thread class'''

    def __init__(self, id, jobDispatcher):
	logger.info("......TaskRunner init is running......")
        threading.Thread.__init__(self)
        self.id = id
        self.task_pool = jobDispatcher.task_pool
        self.session = jobDispatcher.Session()
        self.jobDispatcher = jobDispatcher
        self.debug_soap = jobDispatcher.debug_soap
	logger.info("TaskRunner %s has been created: "%str(id))

    def make_SOAPProxy(self, *args):
        if self.debug_soap:
            return DummySOAPProxy(*args)
        else:
            return SOAPProxy(*args)

    #获得task.content
    #content:
    #op_obj -> 获得task.obj, task.obj.status(根据opToStates) 
    #url    -> 获得proxy
    #op_name-> 获得ServerClass的类方法
    #op_args-> 获得ServerClass的类方法的参数
    #执行ServerClass的类方法后根据返回情况，改变task.status(failed或finished)和task.obj.status(根据failedTransTable,finishedTransTable)
    def do_soapinvoke_task(self, task):
        logger.info('***** do_soapinvoke_task is running *****')
        content = eval(task.content)

        # 获取执行任务的对象
        if content['op_obj']:
            task.obj = InstanceGetter.by_key(content['op_obj'], self.session)
        else:
            task.obj = DummyObject()
	
        # 修改任务状态为在执行
        task.obj.status = opToStates[content['op_job']]
        self.session.commit()

	# 返回一个能调用vmc/server类方法的代理
        proxy = self.make_SOAPProxy(content['url'])

        # 获取vmc/server.py文件里面ServerClass类方法
        invoke_op = getattr(proxy, content['op_name'])

        try:
            logger.debug('start to invoke vmc soap interface %s, the vmc url is %s', content['op_name'], content['url'])
            logger.debug("Args are %s ", content['op_args'])
            # 调用具体执行任务的方法
            res = invoke_op(*content['op_args'])
            logger.debug("Readh here or not..")
            if res is not None:
                if res < 0:
                    task.status = 'failed'
                    task.obj.status = failedTransTable[task.obj.status]

                    if content['op_job'].strip() in ('vmotion', 'add') and task.depend_task_id is None:
                        # 热迁移、添加主机多任务状态保持问题
                        task.obj.status = opToStates[content['op_job']]
                    else:
                        # 修改任务状态为执行完成
                        task.obj.status = finishedTransTable[task.obj.status]
                        task.task_info = '%s result: %s;' % (task.task_info, resTransTable[str(0)])
            else:
                task.status = 'finished'
                task.obj.status = finishedTransTable[task.obj.status]
            self.session.commit()
        except Exception as e:
            logger.error('do_soapinvoke_task is error: %s' % e)
	    task.status = 'failed'
            task.obj.status = failedTransTable[task.obj.status]
            if content['op_name'] == 'migrateVM':
                task.obj.target_vmc_id = None
            self.session.commit()
            raise

    # 更新任务的状态为待执行
    # 把task.status:pending --> scheduling
    def __update_task_status(self, taskid):
        logger.info('***** __update_task_status is running *****')
        try:
            # 执行多任务job时，会出现task状态缓存的情况（status一直为waiting）
            self.session.close()
            task = self.session.query(Task).get(taskid)
            logger.info('task status: %s' % task.status)
            if task.status != 'pending':
		logger.info('task status: %s', task.status)
                return True
            else:
                task.status = 'scheduling'
                self.session.commit()
                return False
        except Exception as e:
            logger.error('__update_task_status is error: %s' % e)
            return True

    #***** __update_task_status is running *****(把task.status:pending --> scheduling)  
    #执行do_soapinvoke_task(task)
    def do_task(self, taskid):
        logger.info('***** do_task is running *****')
        logger.info('taskid value: %s' % taskid)
        try:
            i = 0
            while True:
                try:
                    res = self.__update_task_status(taskid)
                    break
                except Exception as e:
                    self.session.clear()
                    time.sleep(1)
                    if i == 2:
                        logger.error('error executing task %s: %s', taskid, e)
                        logger.exception(e)
                        # task.task_info = '%s task exception: error executing task %s' % (task.task_info, e)
                        # task.status = 'failed'
                        self.session.commit()
                        break
                    logger.debug('try to update task %d status again', taskid)
                finally:
                    i += 1

            # 状态为waiting的任务稍后执行
            if res:
		logger.info('task: %s waiting execute' % taskid)
                return

            task = self.session.query(Task).get(taskid)

            # 当前任务类型都是soapinvoke，所有调用的方法都是do_soapinvoke_task
            adapter_name = 'do_%s_task' % task.task_type
            try:
                adapter = getattr(self, adapter_name)
            except AttributeError:
                logger.error('error, unknown task type %s', task.task_type)
                task.task_info = '%stask exception: unknown task type %s;' % (task.task_info, task.task_type)
                task.status = 'failed'
                self.session.commit()
                return

            try:
                adapter(task)
            except Exception as e:
                logger.error('error executing task %d: %s', task.id, e)
                logger.exception(e)
                task.task_info = '%stask exception: error executing task%s;' % (task.task_info, e)
                task.status = 'failed'
                self.session.commit()
                return
        except Exception as e:
            logger.error('do_task is error: %s' % e)
            self.session.close()

    def run(self):
        logger.info('taskrunner[%d] started' % self.id)
        logger.debug('taskrunner[%d] waiting for task' % self.id)
        logger.info(self.task_pool)
	logger.info("try2")
        while self.jobDispatcher.running:
            try:
                # 依次从队列中取出任务
                taskid = self.task_pool.get(True, 1)
		logger.info("try1")
                try:
		    logger.info("get1")
                    task = self.session.query(Task).get(taskid)
                    logger.info('taskid value: %s' % taskid)
                    if task is None:
                        time.sleep(0.5)
                        self.session.commit()
                        task = self.session.query(Task).get(taskid)
                except Exception as e:
                    logger.error('run is error: %s' % e)
                    raise Exception(e)

                logger.info('task id value: %s' % task.id)
                self.session.expunge_all()
                logger.debug('taskrunner[%d] started task %d %s', self.id, task.id, task.title)
                # 执行任务
                self.do_task(taskid)
                logger.debug('taskrunner[%d] finished task %d %s', self.id, task.id, task.title)
                self.session.expunge_all()
            except Exception as e:
                pass

        logger.info('taskrunner[%d] stopped' % self.id)


jobKey2Mapper = {'vmi': VirtualMachineInstance, 'snapshot': Snapshot, 'vmc': VirtualMachineContainer, 'vmt': VmTemp,
                 'storage': Storage, 'pcluster': PhysicalCluster}
jobOps = ['deploy', 'start', 'stop', 'undeploy', 'migrate', 'vmotion', 'pause', 'snapshot', 'createsnapshot',
          'deletesnapshot', 'rollback', 'resume', 'clone', 'create', 'createt', 'restart', 'config', 'add', 'update',
          'delete', 'check', 'hastart', 'hastop', 'hamigrate']  # add createt by cuilei, dy


class TaskGenerator:
    # 随机获取一个物理主机ID
    def __find_vmc(self, job):
        vmcs = self.s.query(VirtualMachineContainer).filter(
            and_(VirtualMachineContainer.status == 'online', VirtualMachineContainer.capability.like('%vmc%'))).all()
        idx = random.randint(0, len(vmcs) - 1)
        return vmcs[idx]

    # 生成克隆操作的xml模板
    def __generate_clone_task_xml(self, vm, job):
        doc = minidom.parseString(vm.settings.encode("utf-8")).documentElement
        return doc.toxml()

    def __get_address_md5(self, new_address, old_address=None):
        logger.info('***** __get_address_md5 is running *****')
        config = Config.load(project_path('/etc/hicloud/vsched.yaml'))
        md5_address_path = '%s/vmc/md5_address.json' % config['data_dir']
        if not os.path.exists(md5_address_path):
            os.system('touch %s' % md5_address_path)

        address2md5 = {}
        with open(md5_address_path, 'r') as md5_file:
            content = md5_file.read()
            if content.strip() != '':
                address2md5 = eval(content)

        try:
            for address in (new_address, old_address):
                if address is None:
                    continue

                if address2md5.has_key(address):
                    address_md5 = address2md5[address]
                    logger.info('added address: %s, md5: %s' % (address, address_md5))
                else:
                    address_md5 = hashlib.md5('%s %s' % (address, time.strftime('%Y-%m-%d %H:%M:%S'))).hexdigest()
                    address2md5[address] = address_md5
                    logger.info('new address: %s, md5: %s' % (address, address_md5))

            # 互换IP和md5对应值
            if old_address is not None:
                old_md5 = address2md5.pop(old_address)
                new_md5 = address2md5.pop(new_address)
                address2md5[new_address] = old_md5
                address2md5[old_address] = new_md5
                address2info = {'new_address': new_address, 'new_md5': old_md5, 'old_address': old_address,
                                'old_md5': new_md5}
            else:
                address2info = {'new_address': new_address, 'new_md5': address2md5[new_address]}

            with open(md5_address_path, 'w') as md5_file:
                md5_file.write(repr(address2md5))
            return address2info
        except Exception as e:
            logger.error('__set_md5_address is error: %s' % repr(e))

    # 指定虚拟机要完成的任务内容
    def __generate_vmi_task_content(self, vm, job):
        logger.info('***** __generate_vmi_task_content is running *****')
        try:
            # 如果没有选取物理主机，随机选取一个物理主机
            if not vm.virtual_machine_container_id:
                vmc = self.__find_vmc(job)
                logger.debug('allocate vmc %s (id:%d) to vm %d', vmc.address, vmc.id, vm.id)
                vm.virtual_machine_container_id = vmc.id
            else:
                vmc = self.s.query(VirtualMachineContainer).get(vm.virtual_machine_container_id)

            content = {}
            content['url'] = get_vmc_url(vmc.address, vmc.port)
            content['op_job'] = job.optype
            content['op_name'] = '%sSVM' % job.optype  # the only difference between vmi_content and vm_content

            # 判断执行任务的对象
            mapper = type(job.obj)
            keys = {
                VirtualMachineInstance: 'vmi',
            }

            if job.optype in ['deploy', 'create', 'start']:       ################################
                # 指定从镜像创建虚拟机和从模板创建虚拟机的任务内容
                content['op_args'] = [vm.uuid, vm.settings]
            # elif job.optype == 'starttemp':
            #    content['op_args'] = [vm.uuid, vm.settings]
            elif job.optype == 'clone':
                # 指定克隆任务内容
                xml = self.__generate_clone_task_xml(vm, job)
                tmpvm = self.s.query(VirtualMachineInstance).get(int(job.vm_id))
                content['op_args'] = [tmpvm.uuid, xml]
            elif job.optype == 'vmotion':
                # 执行热迁移任务内容
                vmcs = self.__get_vmi_migrate_vmcs(job)
                content['op_args'] = [vm.uuid, vmcs['dst_vmc'].address, vmcs['dst_vmc'].user_name,
                                      vmcs['dst_vmc'].password]
            elif job.optype == 'migrate':
                # 执行冷迁移任务内容
                vmcs = self.__get_vmi_migrate_vmcs(job)
                content['url'] = get_vmc_url(vmcs['dst_vmc'].address, vmcs['dst_vmc'].port)
                content['op_name'] = 'deploySVMInfo'
                content['op_args'] = [vm.uuid, vm.settings, vmcs['src_vmc'].address, vmcs['src_vmc'].user_name,
                                      vmcs['src_vmc'].password]
            elif job.optype in ['createsnapshot']:
                # 创建快照任务内容
                content['op_name'] = 'snapshotSVM'
                content['op_args'] = [vm.uuid, job.snapshot_name]
            elif job.optype in ['deletesnapshot']:
                # 删除快照任务内容
                content['op_name'] = 'deletesnapshotSVM'
                content['op_args'] = [vm.uuid, job.snapshot_name]
            elif job.optype == 'config':
                content['op_args'] = self.__vmi_config_op_args(job)
            elif job.optype in ['snapshot', 'rollback']:
                # 指定快照回滚任务内容
                content['op_args'] = [vm.uuid, job.snapshot_name]
            elif job.optype == 'stop':                          #####################################
                # 指定停止操作任务命令
                stop_mode = 'destroy'
                content['op_args'] = [vm.uuid, stop_mode]
            else:
                content['op_args'] = [vm.uuid]

            # 生成执行操作的对象元素和ID
            content['op_obj'] = InstanceGetter.to_key(vm)
            return repr(content)
        except Exception as e:
            logger.error('__generate_vmi_task_content is error: %s' % e.message)

    # 创建新任务
    def __new_task(self, job):
        logger.info('***** __new_task is running *****')
        task = Task()
        task.uuid = GenUUID()
        task.job_id = job.id
        task.task_type = 'soapinvoke'
        task.status = 'pending'
        task.task_info = ''
        self.s.add(task)
        self.s.commit()
        logger.debug('saving %s', task)
        return task

    def __vmt_taskids(self, job):
        logger.info('***** __vmt_taskids is running *****')
        try:
            if job.optype == 'create':
                vmt = self.s.query(VmTemp).filter(job.obj.id == VmTemp.id)[0]  # get template
                vmi = self.s.query(VirtualMachineInstance).get(vmt.ref_vmi_id)
                tasks = []
                task = self.__new_task(job)
                task.description = "create template"
                task.title = task.description
                vmc = self.s.query(VirtualMachineContainer).get(vmi.virtual_machine_container_id)  # get the first vmc
                if vmc == None:
                    # TODO:
                    pass
                content = {}
                content['op_obj'] = InstanceGetter.to_key(job.obj)
                content['url'] = get_vmc_url(vmc.address, vmc.port)
                content['op_name'] = '%sVMT' % job.optype
                content['op_job'] = job.optype
                content['op_args'] = [vmt.prefer_settings]
                task.content = repr(content)
                self.s.commit()
                tasks.append(task.id)
                return tasks
            else:
                logger.info('Unsupported operation type: %s' % job.optype)
                return []
        except Exception as e:
            logger.error('__vmt_taskids is error: %s' % e)

    def __vmi_taskids(self, job):
        logger.info('***** __vmi_taskids is running *****')
        try:
            if job.optype == 'migrate':
                return self.__vmi_new_migrate_taskids(job)
            if job.optype == 'vmotion':
                return self.__vmi_new_vmotion_taskids(job)
            if job.optype == 'restart':
                return self.__vmi_restart_taskids(job)
            if job.optype == 'rollback':
                return self.__vmi_rollback_taskids(job)
            elif job.optype == 'createt':  # sepetate for two tasks
                return self.__vmi_create_taskids(job)
            elif job.optype in ['config', 'deploy', 'remove', 'undeploy', 'start', 'stop', 'pause', 'resume',
                                'snapshot', 'createsnapshot', 'deletesnapshot', 'clone', 'create',
                                'check']:  # TODO: This is not sure , modify by dy for unify
                vm = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.id == job.obj.id)[0]
                tasks = []
                task = self.__new_task(job)
                task.description = '%s on vmi %d' % (job.optype, job.obj.id)
                task.title = task.description
                content = {}
                content['op_obj'] = InstanceGetter.to_key(job.obj)
                task.content = self.__generate_vmi_task_content(vm, job)
                self.s.commit()
                tasks.append(task.id)
                return tasks
            else:
                logger.info('Unsupported operation type: %s' % job.optype)
                return []
        except Exception as e:
            logger.error('__vmi_taskids is error: %s' % e)

    # 为物理主机分配任务
    def __vmc_taskids(self, job):
        logger.info('***** __vmc_taskids is running *****')
        try:
            if job.optype == 'add':
                address_md5_info = self.__get_address_md5(job.obj.address)
                logger.info('__get_address_md5 result: %s' % repr(address_md5_info))

                # 指定添加物理主机任务
                tasks = []
                task_addVMC = self.__new_task(job)
                task_addVMC.description = '%s on vmc %d' % (job.optype, job.obj.id)
                task_addVMC.title = task_addVMC.description
                content = {}
                content['url'] = get_vmc_url(job.obj.address, job.obj.port)
                content['op_job'] = job.optype
                content['op_name'] = '%sVMC' % job.optype
                content['op_args'] = [job.obj.host_desc]
                content['op_obj'] = InstanceGetter.to_key(job.obj)
                task_addVMC.content = repr(content)
                self.s.commit()
                tasks.append(task_addVMC.id)

                # 开启ha
                # comment by cuilei, May 2016
                # start_ha_task = self.__start_ha_task(job, job.obj, task_addVMC)
                # if start_ha_task is not None:
                #    tasks.append(start_ha_task.id)

                # 导入虚拟机
                update_vmc_task = self.__update_vmc_tasks(job, 'update')
                update_vmc_task.status = 'waiting'
                update_vmc_task.depend_task_id = task_addVMC.id
                self.s.commit()
                tasks.append(update_vmc_task.id)
                return tasks
            elif job.optype == 'hamigrate':
                return self.__vmi_new_hamigrate_taskids(job)
            elif job.optype == 'update':
                return [self.__update_vmc_tasks(job).id]
            else:
                logger.info('Unsupported operation type: %s' % job.optype)
                return []
        except Exception as e:
            logger.error('__vmc_taskids is error: %s' % e)

    def __start_ha_task(self, job, vmc, add_vmc_task):
        cluster = self.s.query(PhysicalCluster).get(vmc.cluster_id)
        if cluster.feature == 1:  # HA是开启状态
            task_HAstart = self.__new_task(job)
            task_HAstart.description = 'hastart on host %d' % vmc.id
            task_HAstart.title = task_HAstart.description
            content = {}
            content['url'] = get_vmc_url(vmc.address, vmc.port)
            content['op_job'] = 'hastart'
            content['op_name'] = 'hastart'
            content['op_args'] = [str(cluster.id)]
            content['op_obj'] = InstanceGetter.to_key(cluster)
            task_HAstart.depend_task_id = add_vmc_task.id
            task_HAstart.content = repr(content)
            task_HAstart.status = "waiting"
            self.s.commit()
            return task_HAstart
        else:
            return None

    def __pcluster_taskids(self, job):
        logger.info('***** __pcluster_taskids is running *****')
        try:
            if job.optype == 'hastart' or job.optype == 'hastop':
                tasks = []
                vmcs = self.s.query(VirtualMachineContainer).filter(
                    and_(VirtualMachineContainer.status == 'online',
                         VirtualMachineContainer.cluster_id == job.obj.id)).all()
                for vmc in vmcs:
                    task = self.__new_task(job)
                    task.description = '%s on pcluster %d' % (job.optype, job.obj.id)
                    task.title = task.description
                    content = {}
                    content['url'] = get_vmc_url(vmc.address, vmc.port)
                    content['op_job'] = job.optype
                    content['op_name'] = job.optype
                    content['op_args'] = [str(job.obj.id)]
                    logger.info(job.obj)
                    content['op_obj'] = InstanceGetter.to_key(job.obj)
                    task.content = repr(content)
                    self.s.commit()
                    tasks.append(task.id)
                return tasks
            else:
                logger.info('Unsupported operation type: %s' % job.optype)
                return []
        except Exception as e:
            logger.error('__pcluster_taskids is error: %s' % e)

    # 生成存储操作任务
    def __vstore_taskids(self, job):
        logger.info('***** __vstore_taskids is running *****')
        try:
            if job.optype == 'add':
                return self.__add_vstore_tasks(job)
            elif job.optype == 'delete':
                return self.__delete_vstore_tasks(job)
            elif job.optype == 'update':
                return self.__update_vstore_tasks(job)
            else:
                logger.info('Unsupported operation type: %s' % job.optype)
                return []
        except Exception as e:
            logger.error('__vstore_taskids is error: %s' % e)

    def __create_vstore_task(self, job, vmc):
        logger.info('***** __create_vstore_task is running *****')
        try:
            task = self.__new_task(job)
            task.description = '%s on vstore %d' % (job.optype, job.obj.id)
            task.title = task.description
            content = {}
            content['url'] = get_vmc_url(vmc.address, vmc.port)
            content['op_job'] = job.optype
            content['op_name'] = '%sVstore' % job.optype
            content['op_args'] = ['<Vstore><VstoreIp>%s</VstoreIp><VstorePath>%s</VstorePath></Vstore>' % (
                job.obj.ip_address, job.obj.storage_path)]
            logger.info(job.obj)
            content['op_obj'] = InstanceGetter.to_key(job.obj)
            task.content = repr(content)
            self.s.commit()
            return task.id
        except Exception as e:
            logger.error('__create_vstore_task is error: %s' % repr(e))
            return None

    def __add_vstore_tasks(self, job):
        logger.info('***** __add_vstore_task is running *****')
        try:
            address_md5_info = self.__get_address_md5(job.obj.ip_address)
            logger.info('__get_address_md5 result: %s' % repr(address_md5_info))

            tasks = []
            if job.obj.is_iso_storage or self.s.query(VirtualMachineContainer).filter(
                    VirtualMachineContainer.address == job.obj.ip_address).count() == 0:
                # 添加iso存储和独立存储
                vmcs = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.status == 'online')
                for vmc in vmcs:
                    task_id = self.__create_vstore_task(job, vmc)
                    if task_id is not None:
                        tasks.append(task_id)
            else:
                # 添加本地存储
                vmc = \
                    self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.address == job.obj.ip_address)[
                        0]
                task_id = self.__create_vstore_task(job, vmc)
                if task_id is not None:
                    tasks.append(task_id)
            return tasks
        except Exception as e:
            logger.error('__add_vstore_task is error: %s' % repr(e))
            return []

    def __delete_vstore_tasks(self, job):
        logger.info('***** __delete_vstore_task is running *****')
        try:
            address_md5_info = self.__get_address_md5(job.obj.ip_address)
            logger.info('__get_address_md5 result: %s' % repr(address_md5_info))

            tasks = []
            vmcs = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.status == 'online')
            # 向所有在线主机发送删除主机任务
            for vmc in vmcs:
                task_id = self.__create_vstore_task(job, vmc)
                if task_id is not None:
                    tasks.append(task_id)
            return tasks
        except Exception as e:
            logger.error('__delete_vstore_task is error: %s' % repr(e))
            return []

    def __update_vstore_tasks(self, job):
        logger.info('***** __update_vstore_tasks is running *****')
        try:
            address_md5_info = self.__get_address_md5(job.obj.ip_address)
            logger.info('__get_address_md5 result: %s' % repr(address_md5_info))

            tasks = []
            vmcs = self.s.query(VirtualMachineContainer).filter(VirtualMachineContainer.status == 'online')
            for vmc in vmcs:
                task_id = self.__create_vstore_task(job, vmc)
                if task_id is not None:
                    tasks.append(task_id)
            return tasks
        except Exception as e:
            logger.error('__update_vstore_tasks is error: %s' % repr(e))
            return []

    def __update_vmc_tasks(self, job, job_type=None):
        logger.info('***** __update_vmc_tasks is running')
        try:
            if job_type is not None:
                job.optype = job_type
            task = self.__new_task(job)
            task.description = '%s on vmc %d' % (job.optype, job.obj.id)
            task.title = task.description
            content = {}
            vmc = self.s.query(VirtualMachineContainer).get(job.obj.id)
            vmc_addresses = self.s.query(VirtualMachineContainer.address).all()
            storages = self.s.query(Storage).all()
            address2path = {}
            for storage in storages:
                address2path[storage.ip_address] = storage.storage_path
            content['url'] = get_vmc_url(vmc.address, vmc.port)
            content['op_job'] = job.optype
            content['op_name'] = '%sVMC' % job.optype
            content['op_args'] = [vmc.address, repr(address2path), repr(vmc_addresses)]
            content['op_obj'] = InstanceGetter.to_key(job.obj)
            task.content = repr(content)
            self.s.commit()
            return task
        except Exception as e:
            logger.error('__update_vmc_tasks is error: %s' % repr(e))
            return []

    def __vmi_config_op_args(self, job):
        try:
            return [job.obj.uuid,
                    job.obj.settings]  # content or jobinfo, [uuid, setting] TODO: get a way to configure the vm
        except Exception as err:
            logger.error("Generate vmi configure content failed: %s" % str(err))
            return ""

    def __vmi_create_op_args(self, job):
        logger.info('***** __vmi_create_op_args is running *****')
        try:
            args = []
            vm = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.id == job.obj.id)[0]
            op_args = [job.obj.uuid, vm.settings]
            return repr(args)
        except Exception as err:
            logger.error("Generate vmi create content failed: %s" % str(err))
            return []

    def __vmi_createt_op_args(self, job):
        logger.info('***** __vmi_createt_op_args is running *****')
        try:
            args = []
            vmi = self.s.query(VirtualMachineInstance).filter(VirtualMachineInstance.id == job.obj.id)[
                0]  # job refs to vm
            # TODO: if temp_stor_path is null, use default path
            job_content = vmi.settings.split(',')
            content['op_args'] = []
            # op_agrs includes "uuid, temp_name, desc, os_type, mem_size, disk_size, vstore_path, iso_path"
            for item in job_content:
                args.append(item.split('#')[1])
                # or query db to get necessary info such as vm.img_path
            return args
        except Exception as err:
            logger.error("Generate vmi create template content failed: %s" % str(err))
            return []

    def __temp_taskids(self, job):
        logger.info('***** __temp_taskids is running *****')
        try:
            if job.optype == 'create':
                # Create template by cloning a vm
                tasks = []
                task = self.__new_task(job)
                task.description = '%s template from vmi %d' % (job.optype, job.obj.id)
                task.title = task.description
                content = {}
                vmc = self.s.query(VirtualMachineContainer).get(
                    job.obj.virtual_machine_container_id)  # select a vmc to execute task, where is scheduler TODO: algorithm
                content['url'] = get_vmc_url(vmc.address, vmc.port)
                content['op_job'] = job.optype
                content['op_name'] = '%sTemp' % job.optype
                temp_uuid = GenUUID()  # TODO
                vmi = self.s.query(VirtualMachineInstance).get(job.obj.id)  # job refs to vm
                # TODO: if temp_stor_path is null, use default path
                content[
                    'op_args'] = job.content  # or jobinfo , including "temp_name, temp_desc, mem_size, disk_size, mount_method and temp_stor_path'
                content['op_args'].append(temp_uuid, vmi.os_type, )  # TODO
                # or query db to get necessary info such as vm.img_path
                content['op_obj'] = InstanceGetter.to_key(job.obj)
                task.content = repr(content)
                self.s.commit()
                tasks.append(task_id)
                return tasks
            else:
                pass
        except Exception as e:
            logger.error('__temp_taskids is error: %s' % e.message)

    # 得到迁移虚拟主机的目标主机和源主机
    def __get_vmi_migrate_vmcs(self, job):
        logger.info('***** __get_vmi_migrate_vmcs is running *****')
        vmcs = {}
        vmcs['src_vmc'] = self.s.query(VirtualMachineContainer).get(job.obj.virtual_machine_container_id)
        vmcs['dst_vmc'] = self.s.query(VirtualMachineContainer).get(job.obj.target_vmc_id)
        return vmcs

    # 创建虚拟机
    def __vmi_create_taskids(self, job):
        logger.info('***** __vmi_create_taskids is running *****')
        try:
            tasks = []
            task_createVM = self.__new_task(job)
            task_createVM.description = '%s on vmi %d' % (job.optype, job.obj.id)
            task_createVM.title = task_createVM.description
            content = {}
            # Create template or vm by iso
            # Get a vmc to execute this step
            vmcs = self.s.query(VirtualMachineContainer).filter(and_(VirtualMachineContainer.status == 'online',
                                                                     VirtualMachineContainer.capability.like(
                                                                         '%vmc%'))).all()
            if len(vmcs) == 0:
                logger.error("All vms are offline")
                raise Exception, "All vms are offline"
            vmc = vmcs[0]  # use the first online vmc
            content['url'] = get_vmc_url(vmc.address, vmc.port)
            content['op_job'] = job.optype
            content['op_name'] = '%sSVM' % job.optype
            content['op_args'] = [job.obj.uuid, job.obj.settings]
            content['op_obj'] = InstanceGetter.to_key(job.obj)
            task_createVM.content = repr(content)
            self.s.commit()
            last_task_id = task_createVM.id
            tasks.append(task_createVM.id)

            job.optype = 'starttemp'
            task_startVM = self.__new_task(job)
            task_startVM.title = 'start info of vmi %d' % (job.obj.id)
            task_startVM.description = task_startVM.title
            task_startVM.depend_task_id = last_task_id
            task_startVM.content = self.__generate_vmi_task_content(job.obj, job)
            task_startVM.status = "waiting"
            self.s.commit()
            return tasks
        except Exception as e:
            logger.error('__vmi_create_taskids is error: %s' % e.message)

            # 指定重启虚拟机任务

    def __vmi_restart_taskids(self, job):
        logger.info('***** __vmi_restart_taskids is running *****')
        try:
            tasks = []
            job.optype = 'stop'
            task_stopVM = self.__new_task(job)
            task_stopVM.title = 'stop info of vmi %d' % (job.obj.id)
            task_stopVM.description = task_stopVM.title
            task_stopVM.content = self.__generate_vmi_task_content(job.obj, job)
            self.s.commit()
            last_task_id = task_stopVM.id
            tasks.append(task_stopVM.id)

            job.optype = 'start'
            task_startVM = self.__new_task(job)
            task_startVM.description = task_startVM.title
            task_startVM.depend_task_id = last_task_id
            task_startVM.content = self.__generate_vmi_task_content(job.obj, job)
            task_startVM.title = job.title
            task_startVM.status = "waiting"
            self.s.commit()
            return tasks
        except Exception as e:
            logger.error('__vmi_restart_taskids is error: %s' % e.message)

    def __vmi_rollback_taskids(self, job):
        logger.info('***** __vmi_rollback_taskids is running *****')
        try:
            tasks = []
            job.optype = 'rollback'
            task_rollbackVM = self.__new_task(job)
            task_rollbackVM.description = task_rollbackVM.title
            task_rollbackVM.content = self.__generate_vmi_task_content(job.obj, job)
            task_rollbackVM.title = job.title
            task_rollbackVM.status = "pending"
            self.s.commit()
            tasks.append(task_rollbackVM.id)
            return tasks
        except Exception as e:
            logger.error('__vmi_rollback_taskids is error: %s' % e.message)

    def __vmi_new_clone_taskids(self, job):
        logger.info('***** __vmi_new_clone_taskids is running *****')
        try:
            job.optype = 'clone'
            task_cloneVM = self.__new_task(job)
            task_cloneVM.title = job.title
            task_cloneVM.description = task_cloneVM.title
            task_cloneVM.content = self.__generate_vmi_task_content(job.obj, job)
            self.s.commit()
            return tasks
        except Exception as e:
            logger.error('__vmi_new_clone_taskids is error: %s' % e.message)

    # 执行冷迁移
    def __vmi_new_migrate_taskids(self, job):
        logger.info('***** __vmi_new_migrate_taskids is running *****')
        try:
            tasks = []
            vmcs = self.__get_vmi_migrate_vmcs(job)
            task_deployVMInfo = self.__new_task(job)
            task_deployVMInfo.title = 'deploy info of vmi %s' % job.obj.id
            task_deployVMInfo.description = task_deployVMInfo.title
            task_deployVMInfo.content = self.__generate_vmi_task_content(job.obj, job)
            self.s.commit()
            logger.info('migrate task id: %s' % task_deployVMInfo.id)
            tasks.append(task_deployVMInfo.id)
            return tasks
        except Exception as e:
            logger.error('cold migrate is error: %s' % e.message)

    # 执行热迁移
    def __vmi_new_vmotion_taskids(self, job):
        logger.info('***** __vmi_new_vmotion_taskids is running *****')
        try:
            tasks = []
            vmcs = self.__get_vmi_migrate_vmcs(job)
            dst_vmc = vmcs['dst_vmc']
            # 生成目标主机的任务
            src_vmc = vmcs['src_vmc']
            task_deployVMInfo = self.__new_task(job)
            task_deployVMInfo.title = 'deploy info of vmi %s' % job.obj.id
            task_deployVMInfo.description = task_deployVMInfo.title
            content = {}
            content['url'] = get_vmc_url(dst_vmc.address, dst_vmc.port)
            content['op_job'] = 'vmotion'
            content['op_name'] = 'deploySVMInfo'  # a little different from deploySVM
            content['op_args'] = [job.obj.uuid, job.obj.settings, src_vmc.address, src_vmc.user_name, src_vmc.password]
            content['op_obj'] = InstanceGetter.to_key(job.obj)
            task_deployVMInfo.content = repr(content)
            self.s.commit()
            logger.info('migrate task id: %s' % task_deployVMInfo.id)
            tasks.append(task_deployVMInfo.id)

            # 生成源主机的任务
            task_migrateVM = self.__new_task(job)
            task_migrateVM.description = task_migrateVM.title
            # 设置依赖任务，需要等到目标主机任务完成后才能执行
            task_migrateVM.depend_task_id = task_deployVMInfo.id
            task_migrateVM.content = self.__generate_vmi_task_content(job.obj, job)  # use the new vmi function
            task_migrateVM.title = job.title
            task_migrateVM.status = "waiting"
            self.s.commit()
            tasks.append(task_migrateVM.id)

            logger.info('tasks %s' % repr(tasks))
            logger.info('create vmotion task is successful')
            return tasks
        except Exception as e:
            logger.error('hot migrate is error: %s' % e.message)

    def __vmi_new_hamigrate_taskids(self, job):
        logger.info('***** __vmi_new_hamigrate_taskids is running *****')
        try:
            tasks = []
            vmc = self.s.query(VirtualMachineContainer).get(job.obj.id)
            vmi_list = self.s.query(VirtualMachineInstance).filter(
                VirtualMachineInstance.virtual_machine_container_id == vmc.id).all()
            vmc_list = self.s.query(VirtualMachineContainer).filter(
                and_(VirtualMachineContainer.cluster_id == vmc.cluster_id,
                     VirtualMachineContainer.status == 'online', VirtualMachineContainer.id != vmc.id)).all()
            sorted(vmc_list, key=lambda vmc: vmc.mem_free, reverse=True)
            logger.info('@__vmi_new_hamigrate_taskids(), vmi_list.size: %s' % len(vmi_list))
            logger.info('@__vmi_new_hamigrate_taskids(), vmc_list.size: %s' % len(vmc_list))

            ##choose vmc(s) as migrate target###
            m = n = 0
            while True:
                if m >= len(vmc_list):
                    self.s.rollback()  # 回滚
                    logger.error('@__vmi_new_hamigrate_taskids(), rollback!')
                    break
                if n >= len(vmi_list):
                    self.s.commit()  # 提交
                    logger.info('@__vmi_new_hamigrate_taskids(), commit!')
                    break

                tmp0 = int(vmi_list[n].mem_total) if vmi_list[n].mem_total.isdigit() else 0
                tmp1 = int(vmc_list[m].mem_free) if vmc_list[m].mem_free.isdigit() else 0
                logger.info('@__vmi_new_hamigrate_taskids(), %d/%d->%d/%d' % (n, m, tmp0, tmp1))
                if tmp0 < tmp1:
                    tmp = vmi_list[n].status
                    vmi_list[n].mig_info = 'stopped'
                    vmi_list[n].status = 'migrating'
                    vmi_list[n].target_vmc_id = vmc_list[m].id

                    task_deployVMInfo = self.__new_task(job)
                    task_deployVMInfo.title = 'deploy info of vmi %s' % vmi_list[n].id
                    task_deployVMInfo.description = task_deployVMInfo.title
                    content = {}
                    content['url'] = get_vmc_url(vmc_list[m].address, vmc_list[m].port)
                    content['op_job'] = 'migrate'
                    content['op_name'] = 'deploySVMInfo'
                    content['op_args'] = [vmi_list[n].uuid, vmi_list[n].settings, vmc.address, vmc.user_name,
                                          vmc.password]
                    content['op_obj'] = InstanceGetter.to_key(vmi_list[n])
                    task_deployVMInfo.content = repr(content)
                    task_deployVMInfo.status = "pending"
                    self.s.commit()
                    tasks.append(task_deployVMInfo.id)

                    tmp1 -= tmp0  # 减去内存，准备进行下一次比较

                    if tmp == 'running':  # 原来运行状态的虚拟机，迁移之后要自动启动
                        task_startVM = self.__new_task(job)
                        task_startVM.title = job.title
                        task_startVM.description = task_startVM.title
                        content = {}
                        content['url'] = get_vmc_url(vmc_list[m].address, vmc_list[m].port)
                        content['op_job'] = 'start'
                        content['op_name'] = 'startSVM'
                        content['op_args'] = [vmi_list[n].uuid, vmi_list[n].settings]
                        content['op_obj'] = InstanceGetter.to_key(vmi_list[n])
                        task_startVM.content = repr(content)
                        task_startVM.depend_task_id = task_deployVMInfo.id
                        task_startVM.status = "waiting"
                        self.s.commit()
                        tasks.append(task_startVM.id)
                    n += 1
                else:
                    m += 1
            logger.info('succeed to create hamigrate tasks : %s' % repr(tasks))
            return tasks
        except Exception as e:
            logger.error('__vmi_new_hamigrate_taskids is error: %s' % e.message)

    def __delete_vmi(self, vm):  # rewrite this to integate with delete_vmis later
        logger.info('***** __delete_vmi is running *****')
        # recycle ip assigned to the undelployed vm
        required = False
        try:
            logger.info("Start to recycle vm ip:%s" % vm.ip)
            for recycle_ip in vm.ip.split():
                logger.info("Recycle ip:%s" % recycle_ip)
                if vm.ip.strip() == '127.0.0.1':
                    continue
                ip = self.s.query(Ip).filter(Ip.ip == recycle_ip)[0]
                ip.status = 0
                required = True
            if required:
                ip_pool = self.s.query(IpPool).get(ip.ip_pool_id)
                ip_pool.out_of_usage = 0
                self.s.commit()
            logger.info("Recycle ip succesfully")
        except Exception as e:
            logger.error('Recycle ip error: %s, this vm ip will not be recycled' % e.message)

    def __delete_vstore(self, vstore):
        self.s.delete(vstore)
        self.s.commit()

    def taskids(self, job, session):
        logger.info('***** taskids is running *****')
        self.s = session
        mapper = type(job.obj)
        functions = {
            VirtualMachineInstance: self.__vmi_taskids,
            PhysicalCluster: self.__pcluster_taskids,
            VirtualMachineContainer: self.__vmc_taskids,
            VmTemp: self.__vmt_taskids,
            Storage: self.__vstore_taskids
        }
        get_taskids = functions[mapper]
        ret = get_taskids(job)
        return ret

    # 执行删除集群、vlab、虚拟机的任务
    def deleterecords(self, obj, session):
        logger.info('***** deleterecords is running *****')
        self.s = session
        mapper = type(obj)
        functions = {
            VirtualMachineInstance: self.__delete_vmi,
            Storage: self.__delete_vstore
        }
        delete_obj = functions[mapper]
        delete_obj(obj)


taskgen = TaskGenerator()


def jobExceptionHandler(fun):
    def __wrapper(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except BaseException as e:
            logger.debug('jobExceptionHandler caught exception %s: %s', type(e), e.message)
            logger.exception(e)
            logger.debug('jobExceptionHandler set job.status to `failed` and ignores the exception')
            job = args[1]
            if not job.job_info:
                job.job_info = ''
            job.job_info = '%s job exception: %s;' % (job.job_info, e.message)
            job.status = 'failed'
            session = args[0].session
            session.commit()

    return __wrapper


# 关闭主机或者宕机时会进行umount,开机时初始化mount存储
class InitMountJob(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True
        self.config = Config.load(project_path('/tmp/adtp-master/hicloud/vsched.yaml'))
        self.session = get_ScopedSession(self.config['connect_string'])()
	ss = self.session.query(VirtualMachineInstance).all()
	logger.info(ss[0].hostname)
	logger.info("Create an InitMountJob")

    # 为当前所有的vmc分发初始化mount任务
    def do_mount_task(self):
        logger.info('***** do_mount_task is running *****')
        content = self.get_vstore_info()
        if content is None:
            return

        for host_ip, task_args in content.items():
	    try:
                vmc = self.session.query(VirtualMachineContainer).filter(VirtualMachineContainer.address == host_ip)[0]
                vmc_url = get_vmc_url(vmc.address, vmc.port)

                logger.info('vmc_url value: %s' % vmc_url)
		print "create a SOAPProxy:%s"%vmc_url
                proxy = SOAPProxy(vmc_url)
		print "create a SOAPProxy end:%s"%vmc_url
                invoke_op = getattr(proxy, 'init_mount_store')
                for args in task_args:
		    print 'args value: %s' % args
                    logger.info('args value: %s' % args)
                    task_result = invoke_op(args)
                    logger.info('init mount result: %s' % task_result)
            except BaseException as e:
                logger.error('assign mount store task is error: %s' % e.message)
                continue
	    
	    
    # 取出当前所有存储信息
    def get_vstore_info(self):
        logger.info('***** get_vstore_info is running *****')
        from ImportedModel import Storage, VirtualMachineContainer, VirtualMachineInstance

        try:
            vmi_instances = self.session.query(VirtualMachineInstance).all()
            # 获取虚机当前使用的所有存储地址列表
            vmc2store2temp = {}
            #for vmi in vmi_instances:
            for i in range(0,2):
		vmi = vmi_instances[i]
	        try:
		    #获得vmi对应的vmc
                    vmc = self.session.query(VirtualMachineContainer).get(vmi.virtual_machine_container_id)  
                    if vmc is None:
                        continue
                except BaseException as e:
                    logger.error('vmc id: %s, error: %s' % (vmi.virtual_machine_container_id, e.message))
                    continue

                if not vmc2store2temp.has_key(str(vmc.address)):
                    vmc2store2temp[str(vmc.address)] = []
		#vmi的配置转化为xml文件
                xmldoc = minidom.parseString(vmi.settings.encode("utf-8"))
                logger.info('%s' % vmi.settings)
		#配置vmc的存储位置信息
                try:  # add by cuilei, May 2016
                    disk_vstore_ip = xmldoc.getElementsByTagName("VstoreIp")[0].firstChild.data
		    logger.info('%s: vmc address: %s' % (i,vmc.address))
		    logger.info('disk_vstore_ip: %s' % disk_vstore_ip)
                    if disk_vstore_ip.strip() == "99999":  # one local VMC address
                        continue
                    vmc2store2temp[vmc.address].append(str(disk_vstore_ip))
                except BaseException as e:
                    logger.error('get element by tag vstoreIp, %s' % e.message)
                    continue
		logger.debug(4)
		#配置vmc的镜像地址
                try:  # add by cuilei, May 2016
		    IsoPath = xmldoc.getElementsByTagName("IsoPath")
		    if(IsoPath[0].firstChild!=None and len(IsoPath[0].firstChild.data.strip())!=0):
                	logger.debug(5)
			logger.debug(IsoPath[0].firstChild.data)
		    	iso_vstore_path = IsoPath[0].firstChild.data
		    	logger.info('iso_vstore_path: %s' % iso_vstore_path)
                    	if iso_vstore_path != 'NON':
                        	vmc2store2temp[vmc.address].append(str(iso_vstore_path.rsplit('/', 2)[1]))
                except BaseException as e:
                    logger.error('get element by tag isoPath error, %s' % e.message)
                    continue
       	    logger.debug(6)
	    for key in vmc2store2temp.keys():
		logger.info(key)
	    for item in vmc2store2temp.items():
		logger.info(item)
	    logger.debug(7) 
            # 处理iso存储和独立存储
            try:
                vmcs = self.session.query(VirtualMachineContainer).all()
		#所有vmc存储ip列表
                vmc_address = [vmc.address for vmc in vmcs if vmc is not None]
		logger.debug("debug1")
		logger.info("length of vmcs: %s"%len(vmcs))
                #if vmcs is not None and vmcs.count() != 0: mod
		if vmcs is not None and len(vmcs)!=0:
                    #iso存储ip列表
		    iso_storages = self.session.query(Storage.ip_address).filter(Storage.is_iso_storage == True).all()
                    logger.debug("debug2")
		    #所有存储ip列表
		    all_storage = self.session.query(Storage).all()
		    logger.info("length of all_storage: %s"%len(all_storage))
		    logger.info("length of iso_storages: %s"%len(iso_storages))
		    logger.info("%s",iso_storages[0])
		    logger.info("1: %s"%all_storage[0].is_iso_storage)
		    logger.info("2: %s"%all_storage[0].storage_path)
		    logger.info("3: %s"%all_storage[0].storage_type)
		    all_storages = self.session.query(Storage.ip_address).all()
		    logger.info(iso_storages)
		    logger.info(all_storages)
                    # 获取独立存储ip列表
                    single_storages = [storage.ip_address for storage in all_storages if
                                       storage.ip_address not in vmc_address]
                    for vmc_address in vmc_address:
                        # 将iso存储挂载到所有主机
                        if iso_storages is not None and len(iso_storages) != 0:
                            if not vmc2store2temp.has_key(vmc_address):
                                vmc2store2temp[vmc_address] = [iso_storages[0].ip_address]
                            else:
                                vmc2store2temp[vmc_address].append(iso_storages[0].ip_address)

                        # 将独立存储挂载到所有主机
                        for storage_address in single_storages:
                            if not vmc2store2temp.has_key(storage_address):
                                vmc2store2temp[vmc_address] = [storage_address]
                            else:
                                vmc2store2temp[vmc_address].append(storage_address)
            except Exception as e:
                logger.info('current not exists iso storage, error: %s' % e.message)

            logger.info('vmc2store2temp value: %s' % repr(vmc2store2temp))
            # 将主机对应的存储去重
            vmc2store = {}
            storage_ips = []
            for key, value in vmc2store2temp.items():
                sub_vtorage_ips = set(value)
                vmc2store[str(key)] = sub_vtorage_ips
                storage_ips.extend(sub_vtorage_ips)

            # 对当前使用的所有存储去重
            storage_ips = set(storage_ips)
            logger.info('storage_ips value: %s' % repr(storage_ips))
            # 根据存储地址获取存储对象
            storage2instance = {}
            for storage_ip in storage_ips:
                if len(storage_ip.strip()) == 0:
                    continue

                try:
                    storage_instance = self.session.query(Storage).filter(Storage.ip_address == storage_ip)[0]
                    storage2instance[storage_ip] = storage_instance
                    logger.info('get %s store instance' % storage_ip)
                except Exception as e:
                    logger.error('storage_ip: %s, error: %s' % (storage_ip, e.message))
                    continue

            logger.info('storage2instance value: %s' % repr(storage2instance))
            # 生成主机挂载存储的对应信息
            vmc2store2info = {}
            for key, value in vmc2store.items():
                logger.info('key, value: %s, %s' % (key, repr(value)))
                vmc2store2info[key] = []
                for store_ip in value:
                    if len(store_ip.strip()) == 0:
                        continue

                    try:
                        vstore_instance = storage2instance[store_ip]
                        vmc2store2info[key].append(
                            {'vstore_ip': vstore_instance.ip_address, 'vstore_path': vstore_instance.storage_path})
                    except Exception as e:
                        logger.error('add vstore info is error: %s' % e.message)
            logger.info('vmc2store2info value: %s' % repr(vmc2store2info))
		
	except BaseException as e:
            vmc2store2info = None
            logger.error('get_vstore_info is error: %s' % e.message)
        return vmc2store2info

    # 初始化新建的存储
    def do_init_storage(self):
        logger.info('do_init_storage() started: %s' % str(self.running))
        while self.running:
            # 取得新建存储列表
            storages = self.session.query(Storage).filter(
                and_(Storage.total_storage == '0', Storage.used_storage == '0')).all()
            if not storages: continue
            # 取得主机列表
            hosts = self.session.query(VirtualMachineContainer).all()
            if not hosts: continue
            # 调用主机，挂接所有的存储
            for host in hosts:
                proxy = SOAPProxy(get_vmc_url(host.address, host.port))
                invoke_op = getattr(proxy, 'init_mount_store')
                for storage in storages:
                    result = invoke_op({'vstore_ip': storage.ip_address, 'vstore_path': storage.storage_path})
                    logger.info('init_mount_store() result: %s' % result)
            logger.info('do_init_storage() go to sleep!')
            time.sleep(1 * 60)  # 休息1分钟
        logger.info('do_init_storage() stopped: %s' % str(self.running))

    def run(self):
        try:
            self.do_mount_task()
            # self.do_init_storage()
        except BaseException as e:
            logger.error('do mount task run() is error: %s' % e.message)

    def stop(self):
        self.running = False


class MonitorLicense(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = True
        self.config = Config.load(project_path('/tmp/adtp-master/hicloud/vsched.yaml'))
        self.session = get_ScopedSession(self.config['connect_string'])()

    def loop_monitor(self):
        while self.running:
            try:
                logger.info('send check license request, cur_time: %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
                hosts = self.session.query(VirtualMachineContainer).all()
                for host in hosts:
                    try:
                        # 如果license验证未通过，将这台vmc设置为离线
                        host.status = 'online'
                        if host.status_flag is not None:
                            host.status_flag = None
                    except Exception as e:
                        logger.info('check host license %s, error: %s' % (host.address, e.message))
                        continue
                    finally:
                        self.session.commit()
            except Exception as e:
                logger.error('monitor license is error: %s' % e.message)
                break
            finally:
                # 每隔五分钟，向vmc发送验证license的请求
                time.sleep(5000 * 60)
                self.session.close()

    def run(self):
        return
        # self.loop_monitor() # add by cuilei, May 2016

    def stop(self):
        self.running = False


class JobDispatcher(threading.Thread):
    '''JobDispatcher thread class'''

    def __init__(self, Session, thread_num=1, debug_soap=False, task_timeout=10, exit_when_no_job=False):
        logger.info("......JobDispatcher init is running......")
        threading.Thread.__init__(self)
        self.Session = Session
        # 为任务池添加先进先出队列，初始大小为0
        self.task_pool = Queue.Queue(0)
        self.running = True
        self.runners = []
        self.exit_when_no_job = exit_when_no_job
        self.debug_soap = debug_soap
        self.task_timeout = task_timeout

        socket.setdefaulttimeout(60 * task_timeout)
	
	logger.info("init a task_pool")	

        for id in range(thread_num):
            r = TaskRunner(id, self)
            r.start()
            self.runners.append(r)

    def stop(self):
        self.running = False

    __objid_fmt0 = re.compile('id:([0-9]+)')
    __objid_fmt1 = re.compile('newcount:([0-9]+)')
    __snapshot_fmt = re.compile('snapshot:(.*)')

    def __change_state(self, instance, optype):
        logger.info('***** __change_state is running *****')
        # logger.info("CHANGE: instance state is " + instance.status)
        logger.info("CHANGE: optype is %s" % optype)
        if (not instance.status in stateOps) or (not optype in stateOps[instance.status]):
            raise LookupError, 'vCluster/vLab/vmi not in expected state'

        instance.status = opToStates[optype]
        self.session.commit()

    def __check_job_obj(self, job):
        logger.info('***** __check_job_obj is running')
        logger.info('job_type value: %s' % job.job_type)
        vtype, optype = job.job_type.split('_')
        if optype == 'scale':
            content0, content1 = job.content.split(',')
            try:
                mat0 = re.search(self.__objid_fmt0, content0)
                mat1 = re.search(self.__objid_fmt1, content1)
                objid = int(mat0.groups()[0])
                count = int(mat1.groups()[0])
            except (AttributeError, TypeError, ValueError):
                raise LookupError, 'job.content fomat is wrong'
        elif optype in ['snapshot', 'rollback', 'createsnapshot', 'deletesnapshot']:
            tokens = job.content.split(',')
            try:
                mat0 = re.search(self.__objid_fmt0, tokens[0])
                mat1 = re.search(self.__snapshot_fmt, tokens[1])
                objid = int(mat0.groups()[0])
                job.vm_id = objid
                job.snapshot_name = mat1.groups()[0]
            except:
                raise LookupError, 'job.content fomat is wrong'
        else:
            # 解析job.content字段，获取操作对象的主键id
            try:
                mat = re.search(self.__objid_fmt0, job.content)
                objid = int(mat.groups()[0])
            except (AttributeError, TypeError, ValueError):
                raise LookupError, 'object id not found in job.content'

        # 获取操作对象的模型实例
        # vtype: 'vmi', 'snapshot', 'vmc', 'vmt', 'storage', 'pcluster'
        # mapper: VirtualMachineInstance, Snapshot, VirtualMachineContainer, VmTemp, Storage, PhysicalCluster
        mapper = jobKey2Mapper[vtype]
        obj = self.session.query(mapper).get(objid)
        if not obj:
            raise LookupError, 'mapper %s, referenced object (id:%d) not found in database' % (mapper, objid)

        if optype == 'scale':
            if count > obj.worknode_count:
                optype = 'scale_more'
            else:
                optype = 'scale_less'

        if optype not in jobOps:
            raise LookupError, 'job_type not supported: %s' % optype

        job.obj = obj
        job.optype = optype
        if optype == 'scale_more' or optype == 'scale_less':
            job.count = count
        # self.__change_state(job.obj, job.optype)

    def __get_pending_jobs(self):
        return self.session.query(Job).filter(Job.status == 'pending')

    def __is_no_scheduling_jobs(self):
        return self.session.query(Job).filter(Job.status == 'scheduling').count() == 0

    def __is_finished_job(self, job):
        condition = and_(Task.job_id == job.id,
                         or_(Task.status == 'scheduling', Task.status == 'pending', Task.status == 'waiting'))
        return self.session.query(Task).filter(condition).count() == 0

    def __get_finished_jobs(self):
        scheduling_jobs = self.session.query(Job).filter(Job.status == 'scheduling')
        return filter(self.__is_finished_job, scheduling_jobs)

    # 判断依赖任务是否结束
    def __is_depending_task_finished(self, task):
        depending_task = self.session.query(Task).get(task.depend_task_id)
        return depending_task and depending_task.status in ['failed', 'finished']

    # 获取依赖任务还没有执行结束的任务
    def __get_waiting_tasks(self):
        depending_tasks = self.session.query(Task).filter(Task.status == 'waiting').filter(Task.depend_task_id > 0)
        return filter(self.__is_depending_task_finished, depending_tasks)

    def __is_job_success(self, job):
        return self.session.query(Task).filter(Task.status == 'failed').filter(Task.job_id == job.id).count() == 0

    def set_scheduling(self, job):
        logger.info('***** set_scheduling is running *****')
        job.status = 'scheduling'
        self.session.commit()

    def __get_job_obj(self, job):
        logger.info('***** __get_job_obj is running *****')
        vtype, optype = job.job_type.split('_')
        if optype == 'scale':
            content0, content1 = job.content.split(',')
            try:
                mat0 = re.search(self.__objid_fmt0, content0)
                mat1 = re.search(self.__objid_fmt1, content1)
                objid = int(mat0.groups()[0])
                count = int(mat1.groups()[0])
            except (AttributeError, TypeError, ValueError):
                raise LookupError, 'job.content fomat is wrong'
        elif optype in ['snapshot', 'rollback']:
            tokens = job.content.split(',')
            try:
                mat0 = re.search(self.__objid_fmt0, tokens[0])
                mat1 = re.search(self.__snapshot_fmt, tokens[1])
                objid = int(mat0.groups()[0])
                job.vm_id = objid
                job.snapshot_name = mat1.groups()[0]
            except:
                raise LookupError, 'job.content fomat is wrong'
        else:
            try:
                mat = re.search(self.__objid_fmt0, job.content)
                objid = int(mat.groups()[0])
            except (AttributeError, TypeError, ValueError):
                raise LookupError, 'object id not found in job.content'
        mapper = jobKey2Mapper[vtype]
        obj = self.session.query(mapper).get(objid)
        # logger.error("obj type is " + vtype)
        # logger.error("obj.id is " + str(obj.id))
        return obj

    def set_failed(self, job):
        logger.info('***** set_failed is running *****')
        if not job.job_info:
            job.job_info = ''
        for task in self.session.query(Task).filter(Task.job_id == job.id):
            job.job_info = '%s task %s: %s ' % (job.job_info, str(task.id), task.task_info)
        job.status = 'failed'
        obj = self.__get_job_obj(job)
        obj.job_id = None
        obj.status = failedTransTable[obj.status]
        task_type = job.job_type.split('_')[1]
        # 添加主机失败时，设置主机状态为离线
        if job.job_type == 'vmc_add':
            obj.status = 'offline'

        if task_type == 'hamigrate':
            tasks = self.session.query(Task).filter(Task.job_id == job.id).all()
            for task in tasks:
                content = eval(task.content)
                if content['op_name'] == 'deploySVMInfo':
                    tmp = InstanceGetter.by_key(content['op_obj'], self.session)
                    tmp.target_vmc_id = None
                    if tmp.mig_info:
                        obj.status = tmp.mig_info
                    tmp.mig_info = None

        # 如果虚拟机迁移失败，虚拟机改回它原来的状态
        if task_type == 'migrate' or task_type == 'vmotion':
            obj.target_vmc_id = None
            if obj.mig_info:
                obj.status = obj.mig_info
            obj.mig_info = None

        # 如果虚拟机快照操作失败，虚拟机改回它原来的状态
        if task_type == 'rollback' or task_type == 'createsnapshot' or task_type == 'deletesnapshot':
            if obj.mig_info:
                obj.status = obj.mig_info  # 虚拟机的状态保存在vmi.mig_info里面
            obj.mig_info = None
        self.session.commit()

    def set_finished(self, job):
        logger.info('***** set_finished is running *****')
        job.status = 'finished'
        obj = self.__get_job_obj(job)
        obj.job_id = None
        logger.info("obj.status is %s" % obj.status)
        obj.status = finishedTransTable[obj.status]
        task_type = job.job_type.split('_')[1]
        if task_type == 'hamigrate':
            tasks = self.session.query(Task).filter(Task.job_id == job.id).all()
            for task in tasks:
                content = eval(task.content)
                if content['op_name'] == 'deploySVMInfo':
                    tmp = InstanceGetter.by_key(content['op_obj'], self.session)
                    if tmp.target_vmc_id: tmp.virtual_machine_container_id = tmp.target_vmc_id
                    tmp.target_vmc_id = None
                    if tmp.mig_info:
                        tmp.status = tmp.mig_info  # 如果虚拟机迁移成功，虚拟机改回它原来的状态
                    tmp.mig_info = None
                    # 如果迁移成功，就删除旧的快照
                    self.session.query(Snapshot).filter(Snapshot.vm_id == tmp.id).delete()
                    ###########################

        if task_type == 'migrate' or task_type == 'vmotion':
            if obj.target_vmc_id:
                obj.virtual_machine_container_id = obj.target_vmc_id
            obj.target_vmc_id = None
            if obj.mig_info:
                obj.status = obj.mig_info  # 如果虚拟机迁移成功，虚拟机改回它原来的状态
            obj.mig_info = None
            # 如果迁移成功，就删除旧的快照
            self.session.query(Snapshot).filter(Snapshot.vm_id == obj.id).delete()
            ###########################

        # 如果虚拟机恢复快照成功，虚拟机改成快照所保存的状态
        if task_type == 'rollback':
            tmp = \
                self.session.query(Snapshot).filter(
                    and_(Snapshot.name == job.snapshot_name, Snapshot.vm_id == job.vm_id))[
                    0]
            if tmp.reserved:
                obj.status = tmp.reserved  # 快照的状态保存在snapshot.reserve里面
            obj.mig_info = None

        if task_type == 'createsnapshot' or task_type == 'deletesnapshot':
            if obj.mig_info:
                obj.status = obj.mig_info  # 虚拟机的状态保存在vmi.mig_info里面
            obj.mig_info = None

        if task_type == 'undeploy' or task_type == 'delete':
            taskgen.deleterecords(obj, self.session)

        if job.job_type == 'vmc_update' or job.job_type == 'vmc_add':
            vmc_url = 'http://%s:8080/vmc/%s' % (obj.address, obj.address)
            logger.info('address: %s, url: %s' % (obj.address, vmc_url))
            tmp_vmc_file = urllib2.urlopen(vmc_url)
            tmp_vmi_content = tmp_vmc_file.read()
            tmp_vmc_file.close()
            logger.info(tmp_vmi_content)
            self.__import_vmis(eval(tmp_vmi_content))
        self.session.commit()

    def __import_vmis(self, vmi2info):
        logger.info('***** __import_vmis is running *****')
        vmis = vmi2info['vmis']
        vmc = \
            self.session.query(VirtualMachineContainer).filter(
                VirtualMachineContainer.address == vmi2info['vmc_address'])[
                0]
        user = self.session.query(User).filter(User.email == 'Administrator')[0]
        for vmi_info in vmis:
            vmi_count = self.session.query(VirtualMachineInstance).filter(
                VirtualMachineInstance.uuid == vmi_info['uuid']).count()
            if vmi_count > 0:
                continue

            if not vmi_info.has_key('disk_size'):
                continue

            vmi = VirtualMachineInstance()
            vmi.uuid = vmi_info['uuid']
            vmi.hostname = vmi_info['name']
            vmi.owner_id = user.id
            vmi.mem_total = vmi_info['mem_size']
            vmi.disk_total = vmi_info['disk_size']
            vmi.cpu_cnt = vmi_info['cpu_count']
            vmi.nic_cnt = vmi_info['nic_count']
            vmi.virtual_machine_container_id = vmc.id
            vmi.status = vmi_info['status']
            vmi.cluster_id = vmc.cluster_id
            ips = [nic2info['address'] for nic2info in vmi_info['interfaces']]
            vmi.ip = ' '.join(ips)
            storage = self.session.query(Storage).filter(Storage.ip_address == vmi_info['vstore_ip'])[0]
            vmi.storage_id = storage.id
            vmi.store_name = vmi_info['ref_temp']
            vmi.oper_system_name = vmi_info['os_type']
            vmi.oper_system_vendor_name = vmi_info['os_version']
            vmi.store_type = vmi_info['iso_path']
            vmi.storeid = vmi_info['vmi_type']
            ip_pool = self.session.query(IpPool).filter(IpPool.vlan == vmi_info['vlan'])[0]
            vmi.reserved = ip_pool.vlan

            nic_settings = []
            for nic2info in vmi_info['interfaces']:
                try:
                    ip = self.session.query(Ip).filter(Ip.ip == nic2info['address'])[0]
                    if ip.status == 0:
                        ip.status = 1
                        self.session.commit()
                except:
                    pass

                nic_settings.append("<NIC>\
                <Address>%s</Address>\
                <MAC>%s</MAC>\
                <Netmask>%s</Netmask>\
                <Gateway>%s</Gateway>\
                <DNS>%s</DNS>\
                </NIC>" % (nic2info['address'],
                           nic2info['mac'],
                           ip_pool.netmask,
                           ip_pool.gateway,
                           ip_pool.dns))

            settings = "<vNode>\
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
            </vNode>" % (
                vmi.uuid,
                vmi_info['vmi_type'],
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
                vmi_info['vmi_type'] == 'Template' and vmi.store_name or 'NON',
                vmi_info['vmi_type'] == 'Iso' and vmi.store_type or 'NON',
                '\n'.join(nic_settings),
                user.password)

            logger.info('deploy settings: %s' % settings)
            vmi.settings = settings
            self.session.add(vmi)
            self.session.commit()

            if vmi_info.has_key('snapshot2info'):
                snapshot2info = vmi_info['snapshot2info']
                # 插入快照的基本信息
                for name, info in snapshot2info.items():
                    try:
                        snapshot = Snapshot()
                        snapshot.name = name
                        snapshot.uuid = GenUUID()
                        snapshot.vm_id = vmi.id
                        snapshot_status = info['state']
                        if info['state'] == 'shutoff':
                            snapshot_status = 'stopped'
                        snapshot.reserved = snapshot_status
                        snapshot.user_id = vmi.owner_id
                        self.session.add(snapshot)
                        self.session.commit()
                    except Exception as e:
                        logger.error('insert snapshot is error: %s' % str(e))

                # 插入快照的父快照信息
                for name, info in snapshot2info.items():
                    try:
                        parent_snapshot_name = info['parent_snapshot_name']
                        if parent_snapshot_name is not None:
                            parent_snapshot = self.session.query(Snapshot).filter(
                                and_(Snapshot.name == parent_snapshot_name, Snapshot.vm_id == vmi.id))[0]
                            snapshot = \
                                self.session.query(Snapshot).filter(
                                    and_(Snapshot.name == name, Snapshot.vm_id == vmi.id))[
                                    0]
                            snapshot.depend_snapshot_id = parent_snapshot.id
                            self.session.commit()
                    except:
                        continue

    # 为待执行job分配任务
    @jobExceptionHandler
    def scheduleJob(self, job):
        logger.info('***** scheduleJob is running *****')
        self.__check_job_obj(job)
        ids = taskgen.taskids(job, self.session)
        self.set_scheduling(job)

        for id in ids:
            self.task_pool.put(id)

    # 标记已完成的job
    @jobExceptionHandler
    def finishJob(self, job):
        logger.info('***** finishJob is running *****')
        if self.__is_job_success(job):
            self.set_finished(job)
        else:
            self.set_failed(job)

    def set_task_timeout(self, task):
        logger.info('***** set_task_timeout is running *****')
        task.status = 'failed'
        task.task_info = 'pending or scheduling time out'
        try:
            content = eval(task.content)
            task.obj = InstanceGetter.by_key(content['op_obj'], self.session)
            task.obj.status = 'error'
            logger.info("timeout commited!")
            self.session.commit()
        except Exception as e:
            task.task_info += '%s;' % str(e)
            pass
        finally:
            self.session.close()

    def do_loop(self):
        cnt = 0
	logger.debug("JobDispatcher do_loop")
        while self.running:
            pending_and_scheduling_tasks = []  # modify by cuilei
            try:
                # 获取处于待执行状态的任务
                pending_and_scheduling_tasks = self.session.query(Task).filter(
                    and_(Task.status != 'finished', Task.status != 'failed')).all()
            except Exception as err:
                cnt = cnt + 1
                logger.error("Get pending and scheduing tasks error: %s" % str(err))
                if cnt == 5:
                    cnt = 0
                    # restart scheduler
                    try:
                        os.system("/etc/init.d/hicloud-daemon restart")
                    except Exception as err:
                        logger.error("Restart scheduler error: %s" % str(err))
            
	    logger.debug("Get pending and scheduling tasks")
	    try:
                for task in pending_and_scheduling_tasks:
                    last_updated_time = task.updated_at
                    pending_or_scheduling_time = time.mktime(datetime.utcnow().timetuple()) - time.mktime(
                        last_updated_time.timetuple())
		    logger.debug('found pending_or_scheduling_time of Task :id:%d, status:%s', task.id, task.status)
                    if pending_or_scheduling_time >= self.task_timeout * 60:
                        logger.debug('found timeout Task :id:%d, status:%s', task.id, task.status)
                        self.set_task_timeout(task)

                # 进行job任务分发 pending job --> scheduling job, 把job中task放进task_pool
		# 配置job的obj,optype
		# 根据job生成相应的task
		# 更新job.status为scheduling
                pending_jobs = self.__get_pending_jobs()
                for job in pending_jobs:
                    logger.debug('found pending Job: id:%d, type:%s, status:%s', job.id, job.job_type, job.status)
                    self.scheduleJob(job)
            except Exception as err:
                logger.error("Schedule job error: %s" % str(err))

            try:
                # 修改job为已完成状态finished，并对job的obj等做修改
                finished_jobs = self.__get_finished_jobs()
                for job in finished_jobs:
                    logger.debug('found finished Job: id:%d, type:%s, status:%s', job.id, job.job_type, job.status)
                    self.finishJob(job)
            except Exception as err:
                logger.error("Finish job error: %s" % str(err))

            try:
                # 执行有依赖关系的任务(status为waiting且所依赖的task都已经结束的task的集合)
		# task状态均改为pending并放入task_pool中
                waiting_tasks = self.__get_waiting_tasks()
                for task in waiting_tasks:
                    logger.debug('found continuable pending Task: id:%d, type:%s, status:%s', task.id, task.task_type,
                                 task.status)
                    task.status = 'pending'
                    self.session.commit()
                    self.task_pool.put(task.id)   
                self.session.commit()
            except Exception as err:
                logger.error("Execute task error: %s" % str(err))

            try:
                #    if self.exit_when_no_job and self.__is_no_scheduling_jobs():
                #        break
                self.session.close()
            except Exception as err:
                logger.error("Close session error: %s" % str(err))
            time.sleep(1)

    def run(self):
        logger.info('jobdispatcher started')
        self.session = self.Session()

        try:
            self.do_loop()
        except Exception as e:
            logger.exception(e)

        self.running = False
        for r in self.runners:
            r.join()

        logger.info('jobdispatcher stopped')


# This is the entry when running as a standalone module
if __name__ == "__main__":
    init_mount_store_job = InitMountJob()
    init_mount_store_job.do_mount_task()
    # init_mount_store_job.start()
    logger.info('hi')
