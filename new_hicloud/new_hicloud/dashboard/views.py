# -*- coding:utf-8 -*-
from django.http import JsonResponse
import SOAPpy

def connect():
    server = SOAPpy.SOAPProxy("")

def get_phy_mac_info(request):
    '''
    获取物理集群信息
    '''
    ret = {'code': 100, 'list': None}

    cluster_on = 1
    cluster_off = 2
    cpu_usage = 1
    mem_usage = 2
    disk_usage = 3
    mem_total = 3
    disk_total = 3

    ret['list'] = {
        'cluster_on': cluster_on, 'cluster_off': cluster_off, 'cpu_usage': cpu_usage, 'mem_usage': mem_usage,
        'disk_usage': disk_usage, 'mem_total': mem_total, 'disk_total': disk_total
    }
    return JsonResponse(ret)
def get_vir_mac_info(request):
    '''
    获取虚拟机信息
    '''
    ret = {'code': 100, 'list': None}

    total_num = 10
    mem_total = 1
    cpu_total = 1
    disk_total = 2

    ret['list'] = {
        'total_num': total_num, 'mem_total': mem_total,
        'cpu_total': cpu_total, 'disk_total': disk_total
    }
    return JsonResponse(ret)