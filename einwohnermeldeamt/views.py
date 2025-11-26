import uuid
import json
import time
import datetime as date
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt 
from fpdf import FPDF #PDF Modul importieren bezüglich Generierung PFD "Meldebestätigung", ansonsten pandas

from urllib.parse import quote  #für Session ID
from .jwt_tooling import create_jwt, decode_jwt  #wichtig damit es funktioniert (Session-ID)

#Module für das Generieren eines Bürger-Passworts
import secrets
import string

# Pfade zu den Registern
personenstandsregister = "/EUER_LINK/personenstandsregister.json"
wohnsitzregister = "/EUER_LINK/wohnsitzregister.json"
adressenregister = "/EUER_LINK/adressenregister.json"

def test_api(request):
    return render(request, "einwohnermeldeamt/test_api.html")


def test(request):
    return render(request, "einwohnermeldeamt/test.html")

def mainpage(request):
    return render(request, "einwohnermeldeamt/mainpage.html")


#Hier zwei Funktionen, für das Aufrufen und Persistieren von Daten im Personenstandsregister

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
def buerger_services(request):

    daten_adressen = lade_adressenregister()
    liste_adressen = daten_adressen.get("adressenregister", [])

    adressen = []
    for neue_adresse in liste_adressen:
        label = f'{neue_adresse["straße_hausnummer"]}, {neue_adresse["plz_ort"]}'
        adressen.append({
            "id": neue_adresse["adresse_id"],
            "label": label
        })

    if request.method == "POST" and request.POST.get("Formulare_Meldeamt") == "wohnsitz":
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

    return render(request, "einwohnermeldeamt/buerger_services.html", {
        "adressen": adressen
    })
    
@csrf_exempt
def standesamt(request):

    daten_personenstand = lade_personenstandsregister()

    if request.method == "POST" and request.POST.get("Formular_Standesamt") == "heirat":
        buerger_id = request.POST.get("buerger_id")
        partner_id = request.POST.get("partner_id")
        neuer_nachname = request.POST.get("neuer_nachname")

        # Bestehende Datensätze beider Personen finden
        person = None
        partner = None

        for eintrag in daten_personenstand:
            if eintrag["buerger_id"] == buerger_id:
                person = eintrag
            if eintrag["buerger_id"] == partner_id:
                partner = eintrag

        # Wenn beide Datensätze existieren → Familienstand ändern
        if person and partner:

            # Familienstand aktualisieren
            person["familienstand"] = "verheiratet"
            person["ehepartner_id"] = partner_id
            person["nachname_neu"] = neuer_nachname

            partner["familienstand"] = "verheiratet"
            partner["ehepartner_id"] = buerger_id
            partner["nachname_neu"] = neuer_nachname

            # Register speichern
            speichere_personenstandsregister(daten_personenstand)

    return render(request, "standesamt/standesamt.html")


#Personenstandsregister muss geladen werden
#Einträge aus Template standesamt übernehmen
#neuer eintrag generiert werden (familienstand muss von ledig auf verheiratet geändert werden, buerger_id verheiratet muss rein ())

#API_URL = "http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/personenstandsregister_api"



#API zwischen Personenstands-Register und Ressort Gesundheit&Soziales


@csrf_exempt                                        #CSRF-Token nur bei POST, PUT und DELETE, nicht bei GET notwendig
def personenstandsregister_api(request):            

    if request.method == "POST":

        vorname = request.POST.get("vorname")
        nachname_geburt = request.POST.get("nachname_geburt")
        geburtsdatum = request.POST.get("geburtsdatum")
        staatsangehoerigkeit = request.POST.get("staatsangehoerigkeit")
        passwort = erstelle_buerger_passwort()      #Korrelation zur Funktion Bürger-Passwort

    #with open("/var/www/django-project/test.txt", "w", encoding="utf-8") as datei:
    #datei.write(str(request.POST))

        erstelle_neuen_eintrag = {
            "buerger_id": str(uuid.uuid4()),
            "public_key": None,                                 #wird rausgegeben für Fachverfahren bei den anderen Ressorts
            "private_key": None,                                #niemals nach außen, bleibt im Personenstandsregister!
            "vorname": vorname,                                 #schickt uns Gesumdheit&Soziales
            "nachname_geburt": nachname_geburt,                 #schickt uns Gesumdheit&Soziales
            "geburtsdatum": geburtsdatum,                       #schickt uns Gesumdheit&Soziales
            "staatsangehoerigkeit": staatsangehoerigkeit,
            "sterbedatum": None,
            "familienstand": "ledig",
            "haft_status": None,
            "steuer_id": None,
        }

        daten = lade_personenstandsregister()
        daten.append(erstelle_neuen_eintrag)
        speichere_personenstandsregister(daten)

        
        return HttpResponse(erstelle_neuen_eintrag["buerger_id"]) #generierte buerger_id als HTTP zurückgeben an Gesundheit&Soziales (PDF als Geburtsurkunde)

    
    return HttpResponse("Nur POST erlaubt", status=405)


#Funktion zur Generierung eines Bürger-Passwortes für den Login (Challenge) auf die Mainpage

def erstelle_buerger_passwort():                            # Anleitung: https://docs.python.org/3/library/secrets.html#secrets.choice
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(5))


### mehrere API's bereitstellen ohne UI fpr alle Ressorts, API (z.B. Suche Vorname + Nachname eine Liste zurückgeben oder anstatt der ID)
### 



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



#Session-ID JWT

##Session-ID versenden

TARGET_URL = "" #Zieladresse!


def fake_login(request):
    request.session["user_id"] = 42
    return HttpResponse("Fake-Login: user_id=42 wurde in die Session geschrieben.")



def session_info(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return HttpResponse("Keine user_id in der Session.")
    return HttpResponse(f"Session user_id: {user_id}")


def weiterleiten(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return HttpResponse("Nicht eingeloggt!", status=401)

    token = create_jwt(user_id)

    redirect_url = f"{TARGET_URL}/jwt-login?token={quote(token)}"    #hier auch nochmal anpassen so wie ihr die URL nennen wollt!
    return redirect(redirect_url) #Token

##Session-ID empfangen


def jwt_login(request):
    token = request.GET.get("token")
    if not token:
        return HttpResponse("Kein Token übergeben.", status=400)

    try:
        daten = decode_jwt(token)
    except Exception:
        return HttpResponse("Ungültiges oder abgelaufenes Token.", status=401)

    user_id = daten.get("user_id")
    if not user_id:
        return HttpResponse("Token enthält keine user_id.", status=400)

    # Session auf Server B setzen
    request.session["user_id"] = user_id

    # Weiter ins Dashboard
    return redirect("mainpage") #hier anpassen, weiterleiten auf die Zielseite