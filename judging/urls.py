from django.urls import path
from . import views

app_name = 'jury'

urlpatterns = [
    # Panel głosowania (jeden link dla jury, bez logowania)
    path('vote/', views.jury_vote_panel, name='vote'),
    path('api/check-session/', views.jury_check_session_api, name='check_session_api'),

    # Skaner QR + parowanie (admin)
    path('scanner/', views.jury_scanner, name='scanner'),
    path('pair/', views.jury_pair_session, name='pair'),
    path('unpair/<int:pk>/', views.jury_unpair_session, name='unpair'),
    path('clear-sessions/', views.jury_clear_sessions, name='clear_sessions'),

    # Członkowie jury (admin)
    path('members/', views.jury_members_list, name='members'),
    path('members/add/', views.jury_members_add, name='members_add'),
    path('members/<int:pk>/delete/', views.jury_member_delete, name='member_delete'),
    path('qr/<uuid:qr_token>/', views.jury_qr_display, name='qr_display'),

    # Prezentacja (admin)
    path('presentation/', views.presentation_panel, name='presentation'),
    path('presentation/next/', views.presentation_next, name='presentation_next'),
    path('presentation/prev/', views.presentation_prev, name='presentation_prev'),
    path('presentation/set/<int:project_pk>/', views.presentation_set_project, name='presentation_set'),

    # Status / sterowanie (admin)
    path('status/', views.hackathon_status_manage, name='status'),

    # Wyniki
    path('results/', views.results, name='results'),
]
