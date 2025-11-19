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
adressenregister = "db/adressenregister.json"



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
        


def lade_adressenregister():
    try:
        with open(adressenregister, "r", encoding="utf-8") as datei:
            return json.load(datei)
    except:
        return {"adressenregister": []}

def lade_wohnsitzregister():
    try:
        with open(wohnsitzregister, "r", encoding="utf-8") as datei:
            return json.load(datei)
    except:
        return []   
    
def speichere_wohnsitzregister(daten):
    with open (wohnsitzregister, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, ensure_ascii=False, indent=2)  


##Funktion zum Speichern Eintrag neuer Wohnsitz in das Wohnsitz-Register

@csrf_exempt
def wohnsitz_anmelden(request):

    daten_adressen = lade_adressenregister()
    liste_adressen = daten_adressen.get("adressenregister", [])

    adressen = []
    for neue_adresse in liste_adressen:
        label = f'{neue_adresse["straße_hausnummer"]}, {neue_adresse["plz_ort"]}'
        adressen.append({
            "id": neue_adresse["adresse_id"],
            "label": label
        })

    if request.method == "POST" and request.POST.get("wohnsitz_anmelden") == "wohnsitz":
        adresse_id = request.POST.get("adresse_id")
        buerger_id = request.POST.get("buerger_id")

        bestehende_adresse = None
        for neue_adresse in liste_adressen:
            if neue_adresse["adresse_id"] == adresse_id:
                bestehende_adresse = neue_adresse
                break

        if bestehende_adresse:
            neuer_eintrag = {
                "meldungsvorgang_id": str(uuid.uuid4()),
                "adresse_id": adresse_id,
                "buerger_id": buerger_id,
                "straße_hausnummer": bestehende_adresse["straße_hausnummer"],
                "plz_ort": bestehende_adresse["plz_ort"],
                "land": bestehende_adresse["land"],
            }

            wohnsitz_daten = lade_wohnsitzregister()
            wohnsitz_daten.append(neuer_eintrag)
            speichere_wohnsitzregister(wohnsitz_daten)

    return render(request, "einwohnermeldeamt/wohnsitz_anmelden.html", {
        "adressen": adressen
    })



#API_URL = "http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/personenstandsregister_api"



#API zwischen Personenstands-Register und Ressort Gesundheit&Soziales

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
            "public_key": None,                     #wird rausgegeben für Fachverfahren bei den anderen Ressorts
            "private_key": None,                    #niemals nach außen, bleibt im Personenstandsregister!
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


#API zwischen Personenstands-Register und den anderen Ressorts

def abfrage_buerger_id(request):
    
    if request.method == "GET":

        vorname = request.GET.get("vorname")
        nachname_geburt = request.GET.get("nachname_geburt")
        geburtsdatum = request.GET.get("geburtsdatum")

        if not (vorname and nachname_geburt and geburtsdatum):
            return JsonResponse(
                {"detail": "Parameter vorname, nachname_geburt und geburtsdatum sind erforderlich."},
                status=400
            )

        daten = lade_personenstandsregister()

        treffer = [
            eintrag for eintrag in daten
            if eintrag.get("vorname") == vorname
            and eintrag.get("nachname_geburt") == nachname_geburt
            and eintrag.get("geburtsdatum") == geburtsdatum
        ]

        if not treffer:
            return JsonResponse({"buerger_ids": [], "anzahl": 0}, status=404)

        ids = [e["buerger_id"] for e in treffer]

        return JsonResponse(
            {
                "buerger_ids": ids,
                "anzahl": len(ids)
            },
            status=200
        )
        
    return JsonResponse({"detail": "Nur GET erlaubt."}, status=405)