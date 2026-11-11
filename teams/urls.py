from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('', views.team_list, name='list'),
    path('<int:pk>/', views.team_detail, name='detail'),
    path('create/', views.team_create, name='create'),
    path('<int:pk>/add-member/', views.add_member, name='add_member'),
    path('<int:pk>/member/<int:member_id>/edit/', views.edit_member, name='edit_member'),
    path('<int:pk>/member/<int:member_id>/remove/', views.remove_member, name='remove_member'),
]
