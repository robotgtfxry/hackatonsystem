from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('', views.team_list, name='list'),
    path('<int:pk>/', views.team_detail, name='detail'),
    path('create/', views.team_create, name='create'),
    path('<int:pk>/add-member/', views.add_member, name='add_member'),
    path('<int:pk>/remove-member/<int:user_id>/', views.remove_member, name='remove_member'),
]
