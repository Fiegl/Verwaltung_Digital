import uuid
import json
import time
import datetime as date
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt 





# Pfade zu den Registern
personenstandsregister = "db/personenstandsregister.json"
wohnsitzregister = "db/wohnsitzregister.json"




def test_api(request):
    return render(request, "einwohnermeldeamt/test_api.html")


def test(request):
    return render(request, "einwohnermeldeamt/test.html")


def lade_personenstandsregister():
    try:
        with open(personenstandsregister, "r", encoding="utf-8") as datei:
            return json.load(datei)
    except:
        return []

    

def speichere_personenstandsregister(daten):
    with open (personenstandsregister, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, ensure_ascii=False, indent=2)
        

def lade_wohnsitzregister():
    try:
        with open(wohnsitzregister, "r", encoding="utf-8") as datei:
            return json.load(datei)
    except:
        return []   
    
    
def speichere_wohnsitzregister(daten):
    with open (wohnsitzregister, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, ensure_ascii=False, indent=2)  

    





#API_URL = "http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/personenstandsregister_api"



@csrf_exempt
def personenstandsregister_api(request):

    if request.method == "POST":

        vorname = request.POST.get("vorname")
        nachname_geburt = request.POST.get("nachname_geburt")
        geburtsdatum = request.POST.get("geburtsdatum")

    #with open("/var/www/django-project/test.txt", "w", encoding="utf-8") as datei:
    #datei.write(str(request.POST))

        erstelle_neuen_eintrag = {
            "buerger_id": str(uuid.uuid4()),
            "vorname": vorname,                     #schickt uns Gesumdheit&Soziales
            "nachname_geburt": nachname_geburt,     #schickt uns Gesumdheit&Soziales
            "geburtsdatum": geburtsdatum,           #schickt uns Gesumdheit&Soziales
            "sterbedatum": None,
            "familienstand": "ledig",
            "haft_status": None,
            "steuer_id": None,
        }

        daten = lade_personenstandsregister()
        daten.append(erstelle_neuen_eintrag)
        speichere_personenstandsregister(daten)

        
        return HttpResponse("Daten gespeichert")

    
    return HttpResponse("Nur POST erlaubt", status=405)


