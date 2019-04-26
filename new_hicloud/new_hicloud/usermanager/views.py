# -*- coding:utf-8 -*-
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User

@csrf_exempt
def register(request):
    '''
    用户注册
    ret = {'code': 100, 'msg': None}
    ret 字典为自定义状态码
    100: 正常
    101: 用户已存在
    102: 数据库读写错误
    '''
    username = request.GET.get('username')
    password = request.GET.get('password')
    email = request.GET.get('email')

    ret = {'code': 100, 'msg': None}

    try:
        exit = User.objects.filter(user_name=username)
        if(len(exit) != 0):
            ret['code'] = 101
            ret['msg'] = u'用户名已存在'
        else:
            result = User(user_name=username, user_passwd=password, user_email=email)
            result.save()
            ret['code'] = 100
            ret['msg'] = u'注册成功'
    except Exception as e:
        print(e)
        ret['code'] = 102
        ret['msg'] = u'数据库读写错误'
    return JsonResponse(ret)

@csrf_exempt
def login_check(request):
    '''
    用户登录
    ret = {'code': 100, 'msg': None}
    ret 字典为自定义状态码
    100: 正常
    101: 用户不存在
    102: 密码错误
    103: 数据库读写错误
    '''
    username = request.GET.get('username')
    password = request.GET.get('password')
    ret = {'code':100, 'msg': None}

    try:
        username_db = User.objects.filter(user_name=username)
        login_result = User.objects.filter(user_name=username, user_passwd=password)
        if (len(username_db) == 0):
            ret['code'] = 101
            ret['msg'] = u'用户不存在'
        else:
            if (len(login_result) == 0):
                ret['code'] = 102
                ret['msg'] = u'密码错误'
            else:
                ret['code'] = 100
                ret['msg'] = u'登录成功'
    except Exception as e:
        ret['code'] = 103
        ret['msg'] = u'数据库读写错误'

    return JsonResponse(ret)

