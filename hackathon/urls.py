from django.urls import path
from . import views

app_name = 'hackathon'

urlpatterns = [
    path('', views.hackathon_detail, name='detail'),
    path('edit/', views.hackathon_edit, name='edit'),
    path('create/', views.hackathon_create, name='create'),
    path('criteria/', views.manage_criteria, name='manage_criteria'),
    path('criteria/<int:criterion_pk>/delete/', views.delete_criterion, name='delete_criterion'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/user/<int:user_id>/role/', views.change_user_role, name='change_user_role'),
    path('admin-panel/user/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin-panel/team/<int:team_id>/delete/', views.delete_team, name='delete_team'),
    path('admin-panel/project/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('delete/', views.delete_hackathon, name='delete_hackathon'),
    path('pdf/wyniki/', views.pdf_results, name='pdf_results'),
    path('pdf/zespoly/', views.pdf_teams, name='pdf_teams'),
]
