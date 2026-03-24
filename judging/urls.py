from django.urls import path
from . import views

app_name = 'judging'

urlpatterns = [
    # Existing
    path('panel/', views.jury_panel, name='panel'),
    path('hackathon/<int:hackathon_pk>/', views.jury_hackathon, name='jury_hackathon'),
    path('score/<int:project_pk>/', views.score_project, name='score_project'),
    path('results/<int:hackathon_pk>/', views.results, name='results'),

    # Jury Members (admin)
    path('members/', views.jury_members_list, name='jury_members_list'),
    path('members/add/', views.jury_members_add, name='jury_members_add'),
    path('members/<int:pk>/delete/', views.jury_member_delete, name='jury_member_delete'),
    path('members/<int:pk>/toggle/', views.jury_member_toggle, name='jury_member_toggle'),

    # QR Code
    path('qr/<uuid:qr_token>/', views.jury_qr_display, name='jury_qr_display'),
    path('session/<uuid:qr_token>/', views.jury_session_login, name='jury_session_login'),
    path('scanner/', views.jury_scanner, name='jury_scanner'),
    path('auth/qr/', views.jury_qr_auth, name='jury_qr_auth'),

    # Voting
    path('vote/', views.jury_vote_panel, name='jury_vote_panel'),
    path('api/current-project/', views.jury_current_project_api, name='jury_current_project_api'),

    # Presentation (admin)
    path('presentation/<int:hackathon_pk>/', views.presentation_panel, name='presentation_panel'),
    path('presentation/<int:hackathon_pk>/next/', views.presentation_next, name='presentation_next'),
    path('presentation/<int:hackathon_pk>/prev/', views.presentation_prev, name='presentation_prev'),
    path('presentation/<int:hackathon_pk>/set/<int:project_pk>/', views.presentation_set_project, name='presentation_set_project'),

    # Global Status
    path('status/', views.hackathon_status_manage, name='hackathon_status_manage'),
    path('api/status/', views.hackathon_status_api, name='hackathon_status_api'),
]
