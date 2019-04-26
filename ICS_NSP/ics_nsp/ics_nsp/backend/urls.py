from django.urls import path
from topology import views
urlpatterns = [
    path('', views.saveTopology)
]