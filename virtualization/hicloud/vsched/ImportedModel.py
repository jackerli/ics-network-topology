# -*- coding: utf-8 -*-

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

#预定义的mac地址
class Macs(Base):
    __tablename__ = 'macs'
   
    id = Column(Integer, primary_key=True)
    status = Column(Integer)
    address = Column(String(255))

# 主机模型
class VirtualMachineContainer(Base):
    __tablename__ = 'virtual_machine_containers'

    id = Column(Integer, primary_key=True)
    hostname = Column(String(255))
    uuid = Column(String(255))
    address = Column(String(255))
    status = Column(String(255))
    running_time = Column(Integer)
    cpu_num = Column(String(255))
    cpu_usage = Column(String(255))
    mem_total = Column(String(255))
    mem_free = Column(String(255))
    disk_total = Column(String(255))
    disk_free = Column(String(255))
    nics_num = Column(Integer)
    vmi_num = Column(Integer)
    max_vmi_num = Column(Integer)

# 虚拟机模型
class VirtualMachineInstance(Base):
    __tablename__ = 'virtual_machine_instances'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(255))
    hostname = Column(String(255))
    virtual_machine_container_id = Column(Integer, ForeignKey('virtual_machine_containers.id'))
    status = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    cpu_usage = Column(String(255))
    mem_total = Column(String(255))
    mem_free = Column(String(255))
    disk_total = Column(String(255))
    disk_free = Column(String(255))
    disk_read = Column(String(255))
    disk_write = Column(String(255))
    vif_tx = Column(String(255))
    vif_rx = Column(String(255))
    vnc_port = Column(String(255))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(Text)
    target_vmc_id = Column(Integer, ForeignKey('virtual_machine_containers.id'))
    mig_info = Column(String(255))
    node_index = Column(Integer)
    capture_nics = Column(String(255))
    capture_expr = Column(String(255))
    capabilities = Column(String(255))
    ip = Column(Text)
    runtime1 = Column(Integer)
    runtime2 = Column(Integer)
    vdisk_names = Column(String(255))
    vif_names = Column(String(255))
    cpu_cnt = Column(Integer)
    memory_keep_capacity = Column(Integer)
    cpu_total_capacity = Column(Integer)
    net_adapter_num = Column(Integer)
    enable_snapshot = Column(String(255))
    power_state = Column(String(255))
    temp_file_name = Column(String(255))
    temp_file_path = Column(String(255))
    storeid = Column(String(255))
    store_name = Column(String(255))
    store_type = Column(String(255))
    vhost_name = Column(String(255))
    vhost_desc = Column(String(255))
    file_name = Column(String(255))
    uuid_bios = Column(String(255))
    oper_system_type = Column(String(255))
    oper_system_version = Column(String(255))
    software_type = Column(String(255))
    network_ids = Column(Text)
    respool_id = Column(Integer)
    cluster_id = Column(Integer)
    dns = Column(String(255))
    nic_cnt = Column(Integer)
    description = Column(String(255))
    group_id = Column(Integer)
    current_snapshot = Column(Integer)
    snapshot_id = Column(Integer)
    reserved = Column(String(255))
    storage_id = Column(Integer)



# IP池模型
class IpPool(Base):
    __tablename__ = 'ip_pools'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(255))
    name = Column(String(255))
    datacenter_id = Column(Integer)
    netmask = Column(String(255))
    gateway = Column(String(255))
    ip_start = Column(String(255))
    ip_end = Column(String(255))
    ip_type = Column(String(255))
    dns = Column(String(255))
    current_ip = Column(String(255))
    out_of_usage = Column(Integer)
    reserved = Column(String(255))
    vlan = Column(Integer)
    ips_count = Column(Integer)

# IP模型
class Ip(Base):
    __tablename__ = 'ips'

    id = Column(Integer, primary_key=True)
    ip = Column(String(15))
    uuid = Column(String(255))
    ip_pool_id = Column(Integer, ForeignKey('ip_pools.id'))
    status = Column(Integer)


# 存储模型
class Storage(Base):
    __tablename__ = 'storages'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(255))
    total_storage = Column(String(255))
    used_storage = Column(String(255))
    storage_type = Column(String(255))
    storage_path = Column(String(255))
    ip_address = Column(String(255))
    name = Column(String(255))
    user_name = Column(String(255))
    password = Column(String(255))
    status = Column(String(255))
    is_iso_storage = Column(Boolean, default=False)
    origin_ip_address = Column(String(255))

class Nics(Base):
    __tablename__ = 'nics'

    id = Column(Integer, primary_key=True)
    address = Column(String(255))
    netmask = Column(String(255))
    vswitch_id = Column(Integer)
    virtual_machine_instance_id = Column(Integer)
    gateway = Column(String(255))
    name = Column(String(255))
    vlan = Column(String(255))
    reserved = Column(Text)

# 交换机模型
class Vswitch(Base):
    __tablename__ = 'vswitches'

    id = Column(Integer, primary_key=True)
    uuid = Column(String(255))
    status = Column(String(255))
    virtual_machine_container_id  = Column(String(255))
    virtual_cluster_instance_id = Column(String(255))
    vlab_instance_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    config_id = Column(Integer)
    connect_type = Column(String(255))
    ip = Column(String(255))
    internet_access = Column(Boolean, default=False)
    netmask = Column(String(255))
    gateway_virtual_machine_container_id = Column(Integer)
    port = Column(Integer)
    tap_num = Column(Integer)
    vmi_num = Column(Integer)


