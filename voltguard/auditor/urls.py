from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.add_appliance, name='add_appliance'),
    path('remove/<int:app_id>/', views.remove_appliance, name='remove_appliance'),
    path('export/', views.export_pdf, name='export_pdf'),
    path('create_project/', views.create_project, name='create_project'),
]
