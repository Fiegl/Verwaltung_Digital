from django.urls import path
from . import views

urlpatterns = [
    path("personenstandsregister_api", views.personenstandsregister_api, name="personenstandsregister_api"), #Slash bei API's weglassen
    path('test/', views.test, name='test'),
    path('test_api/', views.test_api, name="test_api"),
]