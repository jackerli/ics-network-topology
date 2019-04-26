# -*- coding:utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns =[
    url(r'^deployTopo$', views.deployTopo, name='deployTopo'),
    url(r'^startVM$', views.startVM, name='startVM'),
    url(r'^stopVM$', views.stopVM, name='stopVM'),
    url(r'^resumeVM$', views.resumeVM, name='resumeVM'),
    url(r'^pauseVM$', views.pauseVM, name='pauseVM')
]

