from django.urls import path
from . import views

app_name = 'judging'

urlpatterns = [
    path('panel/', views.jury_panel, name='panel'),
    path('hackathon/<int:hackathon_pk>/', views.jury_hackathon, name='jury_hackathon'),
    path('score/<int:project_pk>/', views.score_project, name='score_project'),
    path('results/<int:hackathon_pk>/', views.results, name='results'),
]
