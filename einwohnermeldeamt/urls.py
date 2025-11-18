from django.urls import path
from . import views

urlpatterns = [
    path("personenstandsregister_api", views.personenstandsregister_api, name="personenstandsregister_api"), #Slash bei API's weglassen
    path("wohnsitz_anmelden/", views.wohnsitz_anmelden, name="wohnsitz_anmelden"),
    path("abfrage_buerger_id", views.abfrage_buerger_id, name="abfrage_buerger_id"),
    path('test/', views.test, name='test'),
    path('test_api/', views.test_api, name="test_api"),
]