from django.urls import path
from . import views

urlpatterns = [
    path("personenstandsregister_api", views.personenstandsregister_api, name="personenstandsregister_api"), #Slash bei API's weglassen
    path("buerger_services/", views.buerger_services, name="buerger_services"),
    path("mainpage", views.mainpage, name="mainpage"),
    path('test/', views.test, name='test'),
    path("login", views.login, name="login"),
    path("standesamt", views.standesamt, name="standesamt"),
    
    path('test_api/', views.test_api, name="test_api"),
    path("test_api_setze_beruf/", views.test_api_setze_beruf, name="test_api_setze_beruf"),
    path("test_api_setze_haftstatus/", views.test_api_setze_haftstatus, name="test_api_setze_haftstatus"),
    
    path("api/buerger/beruf", views.setze_beruf, name="setze_beruf"),
    path("api/buerger/haftstatus", views.setze_haftstatus, name="setze_haftstatus"),
    
    
    path("sessiontest/login/", views.fake_login),
    path("sessiontest/info/", views.session_info),
    path("weiterleiten/", views.weiterleiten),
    path("jwt-login", views.jwt_login, name="jwt_login"),
]