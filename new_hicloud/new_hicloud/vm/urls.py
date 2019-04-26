# -*- coding:utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns =[
    url(r'^get_vm_list$', views.get_vm_list, name='get_vm_list'),
    url(r'^start_vm$', views.start_vm, name='start_vm'),
    url(r'^close_vm$', views.close_vm, name='close_vm'),
    url(r'^pause_vm$', views.pause_vm, name='pause_vm'),
    url(r'^resume_vm$', views.resume_vm, name='resume_vm'),
]

