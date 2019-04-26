# -*- coding:utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns =[
    url(r'^get_phy_mac_info$', views.get_phy_mac_info, name='get_phy_mac_info'),
    url(r'^get_vir_mac_info$', views.get_vir_mac_info, name='get_vir_mac_info')
]

