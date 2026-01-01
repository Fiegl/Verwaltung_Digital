import uuid
import json
import os
import datetime
import requests
import datetime as date
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt 
from django.views.decorators.http import require_GET, require_POST
from fpdf import FPDF #PDF Modul importieren bezüglich Generierung PFD "Meldebestätigung", ansonsten pandas

from urllib.parse import quote  #für Session ID
from .jwt_tooling import create_jwt, decode_jwt  #wichtig damit es funktioniert (Session-ID)

#Module für das Generieren eines Bürger-Passworts
import secrets
import string



# Pfade zu den Registern
personenstandsregister = "/var/www/django-project/datenbank/personenstandsregister.json"
wohnsitzregister = "/var/www/django-project/datenbank/wohnsitzregister.json"
adressenregister = "/var/www/django-project/datenbank/adressenregister.json"
dokumentenregister = "/var/www/django-project/datenbank/dokumentenregister.json"
DOKU_BASE = "/var/www/django-project/dokumente"



#Templates zum Testen
def test_api(request):
    return render(request, "einwohnermeldeamt/test_api.html")

def test_api_setze_beruf(request):
    return render(request, "einwohnermeldeamt/test_api_setze_beruf.html")

def test_api_setze_haftstatus(request):
    return render(request, "einwohnermeldeamt/test_api_setze_haftstatus.html")

def test(request):
    return render(request, "einwohnermeldeamt/test.html")


def login(request):
    if request.method == "POST":
        buerger_id = request.POST.get("buerger_id")
        passwort = request.POST.get("passwort")

        daten = lade_personenstandsregister()

        for person in daten:
            if person.get("buerger_id") == buerger_id and person.get("passwort") == passwort:
                request.session["user_id"] = buerger_id
                return redirect("mainpage")

        return render(request, "einwohnermeldeamt/login.html", {
            "error": "Ungültige Bürger-ID oder Passwort."
        })

    return render(request, "einwohnermeldeamt/login.html")

def logout(request):
    request.session.flush()
    return redirect("login")

def mainpage(request):
    if not request.session.get("user_id"):
        return redirect("login")

    return render(request, "einwohnermeldeamt/mainpage.html")

#Hier zwei Hilfs-Funktionen, für das Aufrufen und Persistieren von Daten im Personenstandsregister

def lade_personenstandsregister():
    try:
        with open(personenstandsregister, "r", encoding="utf-8") as datei:
            return json.load(datei)
    except:
        return []

def speichere_personenstandsregister(daten):
    with open (personenstandsregister, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, ensure_ascii=False, indent=2)
        


#Hier eine Hilfs-Funktion, für das Aufrufen und Persistieren von Daten im Adressenregister


def lade_adressenregister():
    try:
        with open(adressenregister, "r", encoding="utf-8") as datei:
            return json.load(datei)
    except:
        return {"adressenregister": []}

#Hier zwei Hilfs-Funktionen für das Aufrufen und Persistieren von Daten im Wohnsitzregister


def lade_wohnsitzregister():
    try:
        with open(wohnsitzregister, "r", encoding="utf-8") as datei:
            return json.load(datei)
    except:
        return []   
    
def speichere_wohnsitzregister(daten):
    with open (wohnsitzregister, "w", encoding="utf-8") as datei:
        json.dump(daten, datei, ensure_ascii=False, indent=2)  

#Hier zwei Hilfsfunktionen für das Aufrufen und Speichern des Dokumenteb-Registers


def lade_dokumentenregister():
    try:
        with open(dokumentenregister, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def speichere_dokumentenregister(docs):
    with open(dokumentenregister, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

def dokument_speichern(buerger_id, typ, pdf_bytes, dateiname):
    ordner = os.path.join(DOKU_BASE, buerger_id)
    os.makedirs(ordner, exist_ok=True)

    pfad = os.path.join(ordner, dateiname)
    with open(pfad, "wb") as f:
        f.write(pdf_bytes)

    docs = lade_dokumentenregister()
    doc_id = str(uuid.uuid4())
    docs.append({
        "doc_id": doc_id,
        "buerger_id": buerger_id,
        "typ": typ,
        "dateiname": dateiname,
        "created_at": datetime.datetime.now().isoformat()
    })
    speichere_dokumentenregister(docs)
    return doc_id

@require_GET
def download_dokument(request, doc_id):
    if not request.session.get("user_id"):
        return redirect("login")

    buerger_id = request.session.get("user_id")

    docs = lade_dokumentenregister()
    doc = None
    for d in docs:
        if d.get("doc_id") == doc_id and d.get("buerger_id") == buerger_id:
            doc = d
            break

    if not doc:
        return HttpResponse("Dokument nicht gefunden", status=404)

    pfad = os.path.join(DOKU_BASE, buerger_id, doc.get("dateiname"))
    if not os.path.exists(pfad):
        return HttpResponse("Datei nicht gefunden", status=404)

    return FileResponse(open(pfad, "rb"), as_attachment=True, filename=doc.get("dateiname"))


@require_GET
def pers_daten(request):
    if not request.session.get("user_id"):
        return redirect("login")

    buerger_id = request.session.get("user_id")

    daten = lade_personenstandsregister()
    person = None
    for p in daten:
        if p.get("buerger_id") == buerger_id:
            person = p
            break

    if not person:
        return HttpResponse("Person nicht gefunden", status=404)

    wohnsitz = hole_wohnsitz_fuer_buerger(buerger_id)

    return render(request, "einwohnermeldeamt/pers_daten.html", {
        "buerger_id": buerger_id,
        "vorname": person.get("vorname"),
        "nachname_geburt": person.get("nachname_geburt"),
        "nachname_neu": person.get("nachname_neu"),
        "geburtsdatum": person.get("geburtsdatum"),
        "wohnsitz": wohnsitz,
    })



def hole_wohnsitz_fuer_buerger(buerger_id):
    daten = lade_wohnsitzregister()

    #Wenn mehrere Einträge existieren, nehmen wir den letzten, also aktuellsten.
    letzter = None
    for eintrag in daten:
        if eintrag.get("buerger_id") == buerger_id:
            letzter = eintrag

    if not letzter:
        return None

    return {
        "straße_hausnummer": letzter.get("straße_hausnummer"),
        "plz_ort": letzter.get("plz_ort"),
        "land": letzter.get("land"),
    }


#globale API für alle Ressorts


@require_GET
def api_person_daten(request, buerger_id):
    daten = lade_personenstandsregister()

    for p in daten:
        if p.get("buerger_id") == buerger_id:
            wohnsitz = hole_wohnsitz_fuer_buerger(buerger_id)

            return JsonResponse(
                {
                    "buerger_id": p.get("buerger_id"),
                    "vorname": p.get("vorname"),
                    "nachname_geburt": p.get("nachname_geburt"),
                    "nachname_neu": p.get("nachname_neu"),
                    "geburtsdatum": p.get("geburtsdatum"),
                    "sterbedatum": p.get("sterbedatum"),
                    "lebensstatus": p.get("lebensstatus"),
                    "familienstand": p.get("familienstand"),
                    "ehepartner_id": p.get("ehepartner_id"),
                    "eheschliessungsdatum": p.get("eheschliessungsdatum"),
                    "haft_status": p.get("haft_status"),
                    "wohnsitz": wohnsitz,
                },
                status=200
            )

    return JsonResponse({"error": "keine_person_gefunden"}, status=404)



##Funktion zum Speichern der Einträge durch die Formulare

@csrf_exempt
def buerger_services(request):
    
    if not request.session.get("user_id"):
        return redirect("login")

    # Adressen für das Formular laden
    daten_adressen = lade_adressenregister()
    liste_adressen = daten_adressen.get("adressenregister", [])

    adressen = []
    for neue_adresse in liste_adressen:
        label = f'{neue_adresse["straße_hausnummer"]}, {neue_adresse["plz_ort"]}'
        adressen.append({
            "id": neue_adresse["adresse_id"],
            "label": label
        })

    #Ab hier laden wir die entsprechenden Formulare
    if request.method != "POST":
        return render(request, "einwohnermeldeamt/buerger_services.html", {
            "adressen": adressen
        })

    vorgang = request.POST.get("Formulare_Meldeamt")

    #Formular Wohnsitz anmelden
    if vorgang == "wohnsitz":
        adresse_id = request.POST.get("adresse_id")
        buerger_id = request.POST.get("buerger_id")

        bestehende_adresse = None
        for neue_adresse in liste_adressen:
            if neue_adresse["adresse_id"] == adresse_id:
                bestehende_adresse = neue_adresse
                break

        daten_personen = lade_personenstandsregister()
        person = None
        for eintrag in daten_personen:
            if eintrag.get("buerger_id") == buerger_id:
                person = eintrag
                break

        if not bestehende_adresse or not person:
            return render(request, "einwohnermeldeamt/buerger_services.html", {
                "adressen": adressen,
                "error": "Bürger-ID oder Adresse nicht gefunden."
            })

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

        datum_heute = date.date.today().strftime("%d.%m.%Y")

        #ab hier erzeugen wir mit dem Modul fPDF die jeweilige PDF für den Bürger, Anleitung: https://py-pdf.github.io/fpdf2/Tutorial-de.html#pdfa-standards
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", style="B", size=16)
        pdf.cell(0, 10, "Meldebestätigung", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("helvetica", size=12)
        textzeilen = [
            "Hiermit wird bestätigt, dass",
            f"{person.get('vorname', '')} {person.get('nachname_geburt', '')}",
            f"am {datum_heute} seinen Wohnsitz an folgender Adresse angemeldet hat:",
            "",
            bestehende_adresse['straße_hausnummer'].replace('_', ' '),
            bestehende_adresse['plz_ort'].replace('_', ' '),
            bestehende_adresse['land'],
            "",
            f"Bürger-ID: {buerger_id}",
            f"Meldungsvorgang-ID: {neuer_eintrag['meldungsvorgang_id']}",
        ]

        for zeile in textzeilen:
            pdf.cell(0, 8, zeile, ln=True)

        pdf_meldebestätigung = pdf.output(dest="S").encode("latin-1")
        dateiname = f"meldebestaetigung_{date.date.today().isoformat()}_{neuer_eintrag['meldungsvorgang_id']}.pdf" 
        dokument_speichern(buerger_id, "meldebestaetigung", pdf_meldebestätigung, dateiname)
        response = HttpResponse(pdf_meldebestätigung, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="meldebestaetigung.pdf"'
        return response

    #Formular Hochzeit
    elif vorgang == "standesamt":
        b_id_1 = request.POST.get("b_id_1") 
        b_id_2 = request.POST.get("b_id_2")  
        eheschliessungsdatum = request.POST.get("eheschliessungsdatum")

        daten_personen = lade_personenstandsregister()

        person1 = None
        person2 = None
        for eintrag in daten_personen:
            if eintrag.get("buerger_id") == b_id_1:
                person1 = eintrag
            if eintrag.get("buerger_id") == b_id_2:
                person2 = eintrag

        if not person1 or not person2:
            return render(request, "einwohnermeldeamt/buerger_services.html", {
                "adressen": adressen,
                "error": "Eine oder beide Bürger-IDs wurden nicht gefunden."
            })

        neuerNachname = person1.get("nachname_geburt")

        person1["familienstand"] = "verheiratet"
        person1["ehepartner_id"] = b_id_2
        person1["eheschliessungsdatum"] = eheschliessungsdatum
        person1["nachname_neu"] = neuerNachname

        person2["familienstand"] = "verheiratet"
        person2["ehepartner_id"] = b_id_1
        person2["eheschliessungsdatum"] = eheschliessungsdatum
        person2["nachname_neu"] = neuerNachname

        speichere_personenstandsregister(daten_personen)

        datum_heute = date.date.today().strftime("%d.%m.%Y")
        datum_ehe = eheschliessungsdatum
        try:
            if eheschliessungsdatum:
                jahr, monat, tag = eheschliessungsdatum.split("-")
                datum_ehe = f"{tag}.{monat}.{jahr}"
        except Exception:
            # Falls irgendwas schiefgeht, einfach Originalstring lassen
            pass

        #ab hier erzeugen wir als PFD die Heiratsurkunde                #XHTML benutzen statt fPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", style="B", size=16)
        pdf.cell(0, 10, "Heiratsurkunde", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("helvetica", size=12)

        name1 = f"{person1.get('vorname', '')} {person1.get('nachname_geburt', '')}"
        name2_geburtsname = f"{person2.get('vorname', '')} {person2.get('nachname_geburt', '')}"
        name2_neu = f"{person2.get('vorname', '')} {neuerNachname}"

        urkundennummer = str(uuid.uuid4())

        textzeilen = [
            f"Urkundennummer: {urkundennummer}",
            "",
            f"Am {datum_ehe} wurde die Ehe geschlossen zwischen",
            f"{name1}",
            "und",
            f"{name2_geburtsname}.",
            "",
            f"Die Person mit der Bürger-ID {b_id_2} führt ab Eheschließung den Familiennamen:",
            f"{neuerNachname}",
            "",
            f"Eintrag im Personenstandsregister vom {datum_heute}.",
        ]

        for zeile in textzeilen:
            pdf.cell(0, 8, zeile, ln=True)

        pdf_hochzeit = pdf.output(dest="S").encode("latin-1")
        dateiname = f"heiratsurkunde_{date.date.today().isoformat()}_{urkundennummer}.pdf"
        dokument_speichern(b_id_1, "heiratsurkunde", pdf_hochzeit, dateiname)
        dokument_speichern(b_id_2, "heiratsurkunde", pdf_hochzeit, dateiname)

        response = HttpResponse(pdf_hochzeit, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="heiratsurkunde.pdf\"'
        return response
    
    
@require_GET
def dokumente(request):
    if not request.session.get("user_id"):
        return redirect("login")

    buerger_id = request.session.get("user_id")
    docs = lade_dokumentenregister()
    docs = [d for d in docs if d.get("buerger_id") == buerger_id]
    docs = sorted(docs, key=lambda x: x.get("created_at", ""), reverse=True)

    return render(request, "einwohnermeldeamt/dokumente.html", {"docs": docs})




#API zwischen Personenstands-Register und Ressort Gesundheit&Soziales

#API_URL = "http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/personenstandsregister_api"



@csrf_exempt                                        #CSRF-Token nur bei POST, PUT und DELETE, nicht bei GET notwendig
def personenstandsregister_api(request):            

    if request.method == "POST":

        vorname = request.POST.get("vorname")
        nachname_geburt = request.POST.get("nachname_geburt")
        geburtsdatum = request.POST.get("geburtsdatum")
        vater_id = request.POST.get("vater_id") or None
        mutter_id = request.POST.get("mutter_id") or None
        passwort = erstelle_buerger_passwort()      #Korrelation zur Funktion Bürger-Passwort

        daten = lade_personenstandsregister()       #hier laden wir das Register, um nach bereits vorhandenen Eltern zu suchen
        
        vater_person = None
        mutter_person = None
        
        if vater_id and mutter_id:
            uuid.UUID(vater_id)
            uuid.UUID(mutter_id)
            
            for person in daten:       #Eltern im Register suchen
                if person.get("buerger_id") == vater_id:
                    vater_person = person
                if person.get("buerger_id") == mutter_id:
                    mutter_person = person
                    
            if not vater_person or not mutter_person:
                return JsonResponse({"error": "eltern nicht gefunden", "vater_gefunden": bool(vater_person), "mutter_gefunden": bool(mutter_person)}, status=400)
        
        neue_buerger_id = str(uuid.uuid4())
        
        erstelle_neuen_eintrag = {
            "buerger_id": neue_buerger_id,
            "private_key": None,                                #niemals nach außen, bleibt im Personenstandsregister!
            "vorname": vorname,                                 #schickt uns Gesumdheit&Soziales
            "nachname_geburt": nachname_geburt,                 #schickt uns Gesumdheit&Soziales
            "geburtsdatum": geburtsdatum,                       #schickt uns Gesumdheit&Soziales
            "sterbedatum": None,                                #schickt uns Gesumdheit&Soziales (bei Todesurkunde)
            "lebensstatus": "lebend",                           #ändert sich bei Tod zu "verstorben"
            "familienstand": "ledig",
            "haft_status": False,                               #Status True oder False (bei Haft-Entlassung) sendet uns Recht&Ordnung
            "passwort": passwort,
            "adresse": None,
            "vater_id": vater_id,
            "mutter_id": mutter_id,
            "kinder_id": []
        }
        #erweitern um Immigration
        
        if vater_person and mutter_person:
            vater_person["kinder_id"].append(neue_buerger_id)
            mutter_person["kinder_id"].append(neue_buerger_id)
        
        
        
        daten.append(erstelle_neuen_eintrag)
        speichere_personenstandsregister(daten)

        #API an Ressort "Steuern&Bank"
        
        url_steuern_bank = "http://[2001:7c0:2320:2:f816:3eff:fe82:34b2]:8000/bank/MELDUNG"  
        
        meldung_data =  {
            "buerger_id": erstelle_neuen_eintrag["buerger_id"],
            "vorname": erstelle_neuen_eintrag["vorname"],
            "nachname": erstelle_neuen_eintrag["nachname_geburt"],
        }  
            
        meldung_data = requests.post(url_steuern_bank, data = meldung_data, timeout=5)


        return HttpResponse(erstelle_neuen_eintrag["buerger_id"])  # generierte buerger_id als HTTP zurückgeben an Gesundheit&Soziales (PDF als Geburtsurkunde)


    return HttpResponse("Bürger im Personenstandsregister eingetragen", status=405)


@csrf_exempt
def personenstandsregister_tod_api(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Nur POST erlaubt"}, status=405)

    # JSON einlesen
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Ungültiges JSON"}, status=400)

    buerger_id = data.get("buerger_id")
    sterbedatum = data.get("sterbedatum")

    if not buerger_id or not sterbedatum:
        return JsonResponse(
            {"detail": "buerger_id und sterbedatum sind erforderlich"},
            status=400
        )

    daten = lade_personenstandsregister()
    gefunden = False

    for person in daten:
        if person.get("buerger_id") == buerger_id:
            person["lebensstatus"] = "verstorben"
            person["sterbedatum"] = sterbedatum
            gefunden = True
            break

    if not gefunden:
        return JsonResponse({"detail": "Bürger nicht gefunden"}, status=404)

    speichere_personenstandsregister(daten)

    return JsonResponse({
        "status": "ok",
        "buerger_id": buerger_id,
        "sterbedatum": sterbedatum
    })


#API an "Beruf&Ausbildung"
        
#url_arbeit_bildung = "http://[2001:7c0:2320:2:f816:3eff:feb6:6731]:8000/api/registrierung"

@require_GET
def api_abfrage_beruf_ausbildung_buerger(request, buerger_id):
    daten = lade_personenstandsregister()

    for p in daten:
        if p.get("buerger_id") == buerger_id:
            wohnsitz = hole_wohnsitz_fuer_buerger(buerger_id)

            eintrag = {
                "buerger_id": p.get("buerger_id"),
                "vorname": p.get("vorname"),
                "nachname_geburt": p.get("nachname_geburt"),
                "geburtsdatum": p.get("geburtsdatum"),
                "haft_status": p.get("haft_status"),
                "nachname_neu": p.get("nachname_neu"),
                "wohnsitz": wohnsitz,
            }

            return JsonResponse(eintrag, status=200)

    return JsonResponse({"error": "keine_person_gefunden"}, status=404)

#curl -g \
#"http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/api/abfrage/beruf_ausbildung/cf26278b-5548-4683-b791-8ece8e909e3f"

#http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/api/abfrage/beruf_ausbildung/cf26278b-5548-4683-b791-8ece8e909e3f

#/einwohnermeldeamt/api/abfrage/beruf_ausbildung/<BUERGER_ID>


#API's Ressort "Recht&Ordnung"

@csrf_exempt
@require_POST
def personensuche_api(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "ungueltiges_json"}, status=400)

    vorname = body["vorname"]
    nachname = body["nachname"]
    geburtsdatum = body["geburtsdatum"]

    daten = lade_personenstandsregister()

    for person in daten:
        if (
            person.get("vorname") == vorname and
            person.get("nachname_geburt") == nachname and
            person.get("geburtsdatum") == geburtsdatum
        ):
            return JsonResponse({"buerger_id": person.get("buerger_id")}, status=200)

    return JsonResponse({"error": "keine_person_gefunden"}, status=404)



@csrf_exempt
@require_POST
def api_setze_haftstatus(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "ungueltiges_json"}, status=400)

    buerger_id = body["buerger_id"]
    haft_status = body["haft_status"]

    daten = lade_personenstandsregister()

    for person in daten:
        if person.get("buerger_id") == buerger_id:
            person["haft_status"] = haft_status
            speichere_personenstandsregister(daten)
            return JsonResponse({"status": "ok", "buerger_id": buerger_id, "haft_status": haft_status}, status=200)

    return JsonResponse({"error": "keine_person_gefunden"}, status=404)




#Funktion zur Generierung eines Bürger-Passwortes für den Login (Sesion-ID (JWT-Token)) auf die Mainpage

def erstelle_buerger_passwort():                            # Anleitung: https://docs.python.org/3/library/secrets.html#secrets.choice
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(5))





#Session-ID JWT

##Session-ID versenden

TARGET_URL = "http://[2001:7c0:2320:2:f816:3eff:feb6:6731]:8000" #Zieladresse von Ressort "Arbeit & Bildung"
#Target URLS so setzen, dass es für alle Kacheln auf der mainpage verweist


def weiterleiten(request):                                  #umschreiben, dass es auf das Personenstandsregister verweist
    buerger_id = request.session.get("user_id")
    if not buerger_id:
        return HttpResponse("Nicht eingeloggt!", status=401)

    token = create_jwt(buerger_id)

    redirect_url = f"{TARGET_URL}/jwt-login?token={quote(token)}"    #hier auch nochmal anpassen so wie ihr die URL nennen wollt!
    return redirect(redirect_url) #Token

TARGET_URL_STEUERN_BANK = "http://[2001:7c0:2320:2:f816:3eff:fe82:34b2]:8000" #Zieladresse von Ressort "Zahlungsverkehr & Steuern"

def weiterleiten_steuern_bank(request):
    buerger_id = request.session.get("user_id")
    if not buerger_id:
        return HttpResponse("Nicht eingeloggt!", status=401)

    token = create_jwt(buerger_id)
    redirect_url = f"{TARGET_URL_STEUERN_BANK}/jwt-login?token={quote(token)}"
    return redirect(redirect_url)    


##Session-ID erzeugen


def jwt_login(request):
    token = request.GET.get("token")
    if not token:
        return HttpResponse("Kein Token übergeben.", status=400)

    try:
        daten = decode_jwt(token)
    except Exception:
        return HttpResponse("Ungültiges oder abgelaufenes Token.", status=401)

    buerger_id = daten.get("user_id")
    if not buerger_id:
        return HttpResponse("Token enthält keine user_id.", status=400)

    # Session auf Server B setzen
    request.session["user_id"] = buerger_id

    # Weiter ins Dashboard
    return redirect("mainpage") #hier anpassen, weiterleiten auf die Zielseite









