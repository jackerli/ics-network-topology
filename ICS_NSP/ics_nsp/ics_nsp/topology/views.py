from django.http import JsonResponse
import socket

def connect(request):
    ret = {'code': 100, 'msg': ''}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('172.20.0.234', 8005))
    try:
        temp = request
        temp1 = str.encode(temp)
        sock.send(temp1)
        res = str(sock.recv(4096), 'utf8')
        print(res)
        ret['code'] = 100
        ret['msg'] = res
    except Exception as e:
        ret['code'] = 101
        ret['msg'] = 'socket connect error!'
        print(e)

    sock.close()
    return ret


def deployTopo(request):
    '''
    部署网络
    '''
    ret = {'code': 100, 'msg': ''}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('172.20.0.234', 8005))

    try:
        temp = 'deployNet'
        temp1 = str.encode(temp)
        sock.send(temp1)
        res = str(sock.recv(8192), 'utf8')
        if res:
            tmp = res.split(" ")
            ret['list'] = []
            temp = {}
            for i in range(len(tmp)):
                if (i == 0):
                    continue
                elif (i % 2 != 0):
                    str_split = tmp[i].split("-", 4)
                    temp['name'] = str_split[3]
                    temp['uuid'] = str_split[4]
                elif (i % 2 == 0):
                    temp['id'] = i / 2
                    temp['ip_addr'] = tmp[i]
                    new_temp = temp.copy()
                    ret['list'].append(new_temp)
            ret['code'] = 100
            ret['msg'] = 'deploy success'
        else:
            ret['code'] = 101
            ret['msg'] = 'socket connect error!'
    except Exception as e:
        ret['code'] = 101
        ret['msg'] = 'socket connect error!'
    sock.close()
    return JsonResponse(ret)


def startVM(request):
    '''
    启动虚拟机
    ret: {'code':100, 'msg': none}
    '''
    uuid = '4e48c0bd-60eb-11e9-a3f1-52540028f1a9'
    # uuid = request.GET.get('uuid')
    str = 'startVMI' + ' ' + uuid
    ret = connect(str)
    print(ret)
    return JsonResponse(ret)


def stopVM(request):
    '''
    关闭虚拟机
    ret: {'code': 100, 'msg':none}
    '''
    uuid = '4e48c0bd-60eb-11e9-a3f1-52540028f1a9'
    # uuid = request.GET.get('uuid')
    str = 'stopVMI' + ' ' + uuid
    ret = connect(str)
    return JsonResponse(ret)


def pauseVM(request):
    '''
    挂起虚拟机
    ret: {'code': 100, 'msg': none}
    '''
    uuid = request.GET.get('uuid')

    str = 'pauseVMI' + ' ' + uuid
    ret = connect(str)
    return JsonResponse(ret)


def resumeVM(request):
    '''
    恢复虚拟机
    ret: {'code': 100, 'msg': none}
    '''
    uuid = request.GET.get('uuid')

    str = 'resumeVMI' + ' ' + uuid
    ret = connect(str)
    return JsonResponse(ret)


def vncConncct(request):
    '''
    noVNC连接
    '''
    uuid = request.GET.get('uuid')
