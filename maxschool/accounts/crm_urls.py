from django.urls import path

from .crm_views import crm_dashboard


urlpatterns = [
    path('', crm_dashboard, name='crm_dashboard'),
]
