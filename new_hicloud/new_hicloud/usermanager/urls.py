# -*- coding:utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns =[
    url(r'^login_check$', views.login_check, name='login_check'),
    url(r'^register$', views.register, name='register')
]

