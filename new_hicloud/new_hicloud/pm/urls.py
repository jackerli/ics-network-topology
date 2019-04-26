# -*- coding:utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns =[
    url(r'^get_phy_mac_list$', views.get_phy_mac_list, name='get_phy_mac_list'),
    url(r'^get_phy_mac_vmlist$', views.get_phy_mac_vmlist, name='get_vir_mac_vmlist')
]

