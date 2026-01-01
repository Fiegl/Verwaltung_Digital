from django.urls import path
from . import views

urlpatterns = [
    path("personenstandsregister_api", views.personenstandsregister_api, name="personenstandsregister_api"), #Slash bei API's weglassen
    path("buerger_services/", views.buerger_services, name="buerger_services"),
    path("mainpage", views.mainpage, name="mainpage"),
    path('test/', views.test, name='test'),
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("dokumente/", views.dokumente, name="dokumente"),
    path("dokumente/<str:doc_id>/download", views.download_dokument, name="download_dokument"),
    path("persoenliche-daten/", views.pers_daten, name="pers_daten"),


    
    path('test_api/', views.test_api, name="test_api"),
    path("test_api_setze_beruf/", views.test_api_setze_beruf, name="test_api_setze_beruf"),
    path("test_api_setze_haftstatus/", views.test_api_setze_haftstatus, name="test_api_setze_haftstatus"),
    
    path("api/person/<str:buerger_id>", views.api_person_daten, name="api_person_daten"),
    
    path("api/personenstandsregister/tod", views.personenstandsregister_tod_api, name="personenstandsregister_tod_api"),
    
    path("api/abfrage/beruf_ausbildung/<str:buerger_id>", views.api_abfrage_beruf_ausbildung_buerger, name="api_abfrage_beruf_ausbildung_buerger"),

    
    path("api/recht-ordnung/personensuche", views.personensuche_api, name="personensuche_api"),
    path("api/recht-ordnung/haftstatus", views.api_setze_haftstatus, name="api_setze_haftstatus"),
    
    
    path("weiterleiten/", views.weiterleiten),
    path("weiterleiten_steuern_bank/", views.weiterleiten_steuern_bank, name="weiterleiten_steuern_bank"),

    path("jwt-login", views.jwt_login, name="jwt_login"),

]