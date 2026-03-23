from django.urls import path
from . import views

app_name = 'hackathon'

urlpatterns = [
    path('', views.hackathon_list, name='list'),
    path('<int:pk>/', views.hackathon_detail, name='detail'),
    path('create/', views.hackathon_create, name='create'),
    path('<int:pk>/edit/', views.hackathon_edit, name='edit'),
    path('<int:pk>/jury/', views.manage_jury, name='manage_jury'),
    path('<int:pk>/criteria/', views.manage_criteria, name='manage_criteria'),
    path('<int:pk>/criteria/<int:criterion_pk>/delete/', views.delete_criterion, name='delete_criterion'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/user/<int:user_id>/role/', views.change_user_role, name='change_user_role'),
]
