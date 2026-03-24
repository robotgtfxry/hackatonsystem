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
    path('admin-panel/user/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin-panel/team/<int:team_id>/delete/', views.delete_team, name='delete_team'),
    path('admin-panel/project/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('<int:pk>/delete/', views.delete_hackathon, name='delete_hackathon'),
]
