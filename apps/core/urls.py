# apps/core/urls.py
from django.urls import path
from . import views as core_views

app_name = 'core'

urlpatterns = [
    path("api/permissions/definir/", core_views.api_definir_permission_role, name="api_definir_permission_role"),
]