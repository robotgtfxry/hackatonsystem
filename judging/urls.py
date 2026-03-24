from django.urls import path
from . import views

app_name = 'judging'

urlpatterns = [
    # Existing (stary system oceniania)
    path('panel/', views.jury_panel, name='panel'),
    path('hackathon/<int:hackathon_pk>/', views.jury_hackathon, name='jury_hackathon'),
    path('score/<int:project_pk>/', views.score_project, name='score_project'),
    path('results/<int:hackathon_pk>/', views.results, name='results'),

    # Jury Members — zarządzanie (admin)
    path('members/', views.jury_members_list, name='jury_members_list'),
    path('members/add/', views.jury_members_add, name='jury_members_add'),
    path('members/<int:pk>/delete/', views.jury_member_delete, name='jury_member_delete'),
    path('members/<int:pk>/toggle/', views.jury_member_toggle, name='jury_member_toggle'),

    # QR — wyświetlanie kodu
    path('qr/<uuid:qr_token>/', views.jury_qr_display, name='jury_qr_display'),

    # Skaner QR (admin)
    path('scanner/', views.jury_scanner, name='jury_scanner'),
    path('auth/qr/', views.jury_qr_auth, name='jury_qr_auth'),
    path('deactivate/<int:pk>/', views.jury_deactivate, name='jury_deactivate'),
    path('deactivate-all/', views.jury_deactivate_all, name='jury_deactivate_all'),

    # Panel głosowania jury (bez logowania — token w URL)
    path('vote/<uuid:qr_token>/', views.jury_vote_panel, name='jury_vote_panel'),
    path('api/current-project/<uuid:qr_token>/', views.jury_current_project_api, name='jury_current_project_api'),

    # Prezentacja (admin)
    path('presentation/<int:hackathon_pk>/', views.presentation_panel, name='presentation_panel'),
    path('presentation/<int:hackathon_pk>/next/', views.presentation_next, name='presentation_next'),
    path('presentation/<int:hackathon_pk>/prev/', views.presentation_prev, name='presentation_prev'),
    path('presentation/<int:hackathon_pk>/set/<int:project_pk>/', views.presentation_set_project, name='presentation_set_project'),

    # Globalny status hackatonu
    path('status/', views.hackathon_status_manage, name='hackathon_status_manage'),
    path('api/status/', views.hackathon_status_api, name='hackathon_status_api'),
]
