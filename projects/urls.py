from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='list'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('submit/<int:team_pk>/', views.project_submit, name='submit'),
    path('<int:pk>/edit/', views.project_edit, name='edit'),
    path('<int:pk>/upload/', views.upload_file, name='upload_file'),
]
