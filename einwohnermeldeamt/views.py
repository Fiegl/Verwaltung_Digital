#  wichtige Befehle für die PowerShell
##
##
##

import uuid
import json
import os
import datetime as dt
import requests
from datetime import date
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt 
from django.views.decorators.http import require_GET, require_POST
from fpdf import FPDF #PDF Modul importieren bezüglich Generierung PFD "Meldebestätigung", ansonsten pandas
from django.conf import settings

from urllib.parse import quote  #für Session ID
from .jwt_tooling import create_jwt, decode_jwt  #wichtig damit es funktioniert (Session-ID)
from django.utils import timezone

from io import BytesIO #pip isnstall pyhanko + pip install pyhanko pyhanko-certvalidator cryptography
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter



# pyHanko (PDF-Signaturen)
try:
    from pyhanko.sign import signers
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko_certvalidator import ValidationContext
    from cryptography import x509
except Exception:
    # Falls pyHanko (noch) nicht installiert ist, fangen wir das unten sauber ab.
    signers = None
    validate_pdf_signature = None
    PdfFileReader = None
    ValidationContext = None
    x509 = None

#Module für das Generieren eines Bürger-Passworts
import secrets
import string





# Pfade zu den Registern
personenstandsregister = "/var/www/django-project/datenbank/personenstandsregister.json"
wohnsitzregister = "/var/www/django-project/datenbank/wohnsitzregister.json"
adressenregister = "/var/www/django-project/datenbank/adressenregister.json"
dokumentenregister = "/var/www/django-project/datenbank/dokumentenregister.json"
mitarbeiterregister = "/var/www/django-project/datenbank/mitarbeiterregister.json"
DOKU_BASE = "/var/www/django-project/dokumente"

##Wichtige Befehle, um Berechtigungen für den Zugriff auf die Register zu setzen (am Beispiel vom Dokumenten-Register):

#sudo mkdir -p /var/www/django-project/dokumente
#sudo chgrp -R www-data /var/www/django-project/dokumente /var/www/django-project/datenbank
#sudo chmod -R 770 /var/www/django-project/dokumente
#sudo chmod 660 /var/www/django-project/datenbank/dokumentenregister.json

#sudo chgrp -R www-data /var/www/django-project/dokumente
#sudo chmod -R 2775 /var/www/django-project/dokumente
#sudo usermod -aG www-data ubuntu



#Templates zum Testen
def test_api(request):
    return render(request, "einwohnermeldeamt/test_api.html")

def test_api_setze_beruf(request):
    return render(request, "einwohnermeldeamt/test_api_setze_beruf.html")

def test_api_setze_haftstatus(request):
    return render(request, "einwohnermeldeamt/test_api_setze_haftstatus.html")

def test(request):
    return render(request, "einwohnermeldeamt/test.html")

##Hier eine Hilfs-Funktion für das Aufrufen des Mitarbeiter-Registerts, darunter eine Funktion zum Prüfen der PIN

def lade_mitarbeiterregister():
    try:
        with open(mitarbeiterregister, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def pruefe_mitarbeiter_pin(buerger_id: str, pin: str) -> dict | None:
    daten = lade_mitarbeiterregister()
    for m in daten:
        if m.get("buerger_id") == buerger_id and m.get("aktiv") is True and m.get("pin") == pin:
            return m
    return None




def login(request):
    if request.method == "POST":
        buerger_id = request.POST.get("buerger_id")
        passwort = request.POST.get("passwort")

        daten = lade_personenstandsregister()

        for person in daten:
            if person.get("buerger_id") == buerger_id and person.get("passwort") == passwort:
                request.session["user_id"] = buerger_id
                request.session["role"] = "buerger"

                request.session["first_name"] = person.get("vorname") or ""
                request.session["last_name"] = person.get("nachname_neu") or person.get("nachname_geburt") or ""

                return redirect("mainpage")

        return render(request, "einwohnermeldeamt/login.html", {"error": "Ungültige Bürger-ID oder Passwort."})

    return render(request, "einwohnermeldeamt/login.html")


def logout(request):
    request.session.flush()
    return redirect("login")

def setze_session_namen(request, buerger_id: str):
    daten = lade_personenstandsregister()
    person = None
    for p in daten:
        if p.get("buerger_id") == buerger_id:
            person = p
            break

    if person:
        request.session["first_name"] = person.get("vorname", "")
        request.session["last_name"] = person.get("nachname_neu") or person.get("nachname_geburt") or ""
    else:
        request.session["first_name"] = ""
        request.session["last_name"] = ""


def finde_person_by_buerger_id(buerger_id):
    daten = lade_personenstandsregister()
    for p in daten:
        if p.get("buerger_id") == buerger_id:
            return p
    return None

def display_name_for_person(p):
    if not p:
        return "Gast"
    nachname = p.get("nachname_neu") or p.get("nachname_geburt") or ""
    vorname = p.get("vorname") or ""
    return f"{vorname} {nachname}".strip()


def mainpage(request):
    buerger_id = request.session.get("user_id")
    if not buerger_id:
        return redirect("login")

    person = finde_person_by_buerger_id(buerger_id)
    return render(request, "einwohnermeldeamt/mainpage.html", {
        "display_name": display_name_for_person(person),
    })


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
        "created_at": dt.datetime.now().isoformat()

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



def signiere_heiratsurkunde_pdf(
    *,
    urkundennummer: str,
    pdf_bytes: bytes,
    aussteller_name: str,
) -> dict:
    """
    Signiert eine fertige PDF (bytes) mit Sarah Webers Zertifikat/Private Key.
    Speichert optional eine Kopie unter /var/www/django-project/signaturen/
    Gibt Metadaten zurück (signed_bytes, sig_filename, sig_path).

    Rückgabe-Keys:
      - signed_pdf_bytes: bytes
      - sig_filename: str
      - sig_path: str
    """

    if signers is None:
        raise RuntimeError(
            "pyHanko ist nicht verfügbar. Installiere: pip install pyhanko pyhanko-certvalidator cryptography"
        )

    # Keys als Dateien (nicht im Register!)
    cert_path = "/var/www/django-project/keys/sarah_cert.pem"
    key_path  = "/var/www/django-project/keys/sarah_privkey.pem"

    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        raise FileNotFoundError(
            "Signatur-Keys fehlen auf dem Server (sarah_cert.pem / sarah_privkey.pem)."
        )

    # SimpleSigner aus Dateien laden
    # (kein Passwort angenommen; falls ihr eins habt: passphrase=b"....")
    signer = signers.SimpleSigner.load(
        key_file=key_path,
        cert_file=cert_path,
        key_passphrase=None,
    )

    # Signatur-Metadaten
    meta = signers.PdfSignatureMetadata(
        field_name="Signature1",  # wird bei Bedarf automatisch angelegt
        reason=f"Heiratsurkunde elektronisch signiert durch {aussteller_name}",
        location="Standesamt",
    )

    pdf_signer = signers.PdfSigner(meta, signer=signer)

    out = BytesIO()

    w = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
    pdf_signer.sign_pdf(w, output=out)

    signed_pdf_bytes = out.getvalue()



    # Optional: Kopie zusätzlich in Signaturen-Ordner ablegen (praktisch fürs Debug/Standesamt-Endpoint)
    out_dir = "/var/www/django-project/signaturen"
    os.makedirs(out_dir, exist_ok=True)

    sig_filename = f"heiratsurkunde_{urkundennummer}.signed.pdf"
    sig_path = os.path.join(out_dir, sig_filename)
    with open(sig_path, "wb") as f:
        f.write(signed_pdf_bytes)

    return {
        "signed_pdf_bytes": signed_pdf_bytes,
        "sig_filename": sig_filename,
        "sig_path": sig_path,
    }


def verify_pdf_signatur_bytes(
    *,
    pdf_bytes: bytes,
    trust_cert_pem_path: str = "/var/www/django-project/keys/sarah_cert.pem",
) -> dict:
    """
    Verifiziert (einfach) die eingebettete PDF-Signatur.
    Rückgabe dict für JSON:
      - ok: bool
      - message: str
      - detail: str (optional)
    """

    if validate_pdf_signature is None or PdfFileReader is None or ValidationContext is None or x509 is None:
        return {
            "ok": False,
            "message": "PDF-Signaturprüfung nicht verfügbar (pyHanko fehlt).",
        }

    if not os.path.exists(trust_cert_pem_path):
        return {"ok": False, "message": "Zertifikat fehlt (sarah_cert.pem)."}

    with open(trust_cert_pem_path, "rb") as f:
        cert_bytes = f.read()

    try:
        trust_cert = x509.load_pem_x509_certificate(cert_bytes)
        vc = ValidationContext(trust_roots=[trust_cert])

        reader = PdfFileReader(BytesIO(pdf_bytes))
        embedded = list(reader.embedded_signatures)

        if not embedded:
            return {"ok": False, "message": "Keine eingebettete Signatur in der PDF gefunden."}

        # Wenn mehrere Signaturen drin sind, nehmen wir die letzte (meist die „aktuellste“)
        sig = embedded[-1]

        status = validate_pdf_signature(sig, vc)

        # bottom_line == True bedeutet im Wesentlichen: kryptografisch OK + chain OK (im Rahmen VC)
        if getattr(status, "bottom_line", False):
            return {"ok": True, "message": "Signatur gültig."}

        # Falls nicht OK, versuchen wir Details lesbar zu machen
        summ = getattr(status, "summary", None)
        return {
            "ok": False,
            "message": "Signatur ungültig oder nicht vertrauenswürdig.",
            "detail": str(summ) if summ else "Validation fehlgeschlagen.",
        }

    except Exception as e:
        return {"ok": False, "message": "Signaturprüfung fehlgeschlagen.", "detail": str(e)}


# ---------------------------------------------------------------------------
# Hier zwei Hilfs-Funktionen für das Einbinden von CSS bei der Erstellung der PDF-Dokumente (fpdf)
# (unverändert lassen – Templates/Layout bleiben gleich)
# ---------------------------------------------------------------------------

def pdf_base(pdf, titel, logo_path=None):
    pdf.add_page()

    # Rahmen
    pdf.set_draw_color(0, 102, 204)
    pdf.set_line_width(2)
    pdf.rect(5, 5, 200, 287)

    # Logo
    if logo_path and os.path.exists(logo_path):
        pdf.image(logo_path, x=165, y=10, w=30)

    pdf.ln(25)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 12, titel, ln=True, align="C")
    pdf.ln(8)


def pdf_meta_block(pdf, lines):
    pdf.set_draw_color(180, 180, 180)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Helvetica", "", 10)
    for line in lines:
        pdf.cell(0, 6, line, ln=True)


# ---------------------------------------------------------------------------
# Funktion zum Speichern der Einträge durch die Formulare
# (nur Standesamt-Teil relevant umgebaut -> PDF signieren statt XML)
# ---------------------------------------------------------------------------

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
        adressen.append({"id": neue_adresse["adresse_id"], "label": label})

    # Ab hier laden wir die entsprechenden Formulare
    if request.method != "POST":
        error = request.session.pop("error", None)
        return render(request, "einwohnermeldeamt/buerger_services.html", {
            "adressen": adressen,
            "error": error
        })

    vorgang = request.POST.get("Formulare_Meldeamt")
    role = request.session.get("role", "buerger")

    # -----------------------------------------------------------------------
    # Formular Wohnsitz anmelden (unverändert)
    # -----------------------------------------------------------------------
    if vorgang == "wohnsitz":

        if role != "buerger":
            return render(request, "einwohnermeldeamt/buerger_services.html", {
                "adressen": adressen,
                "error": "Nur Bürger dürfen Wohnsitz anmelden."
            })

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

        person["adresse"] = adresse_id
        speichere_personenstandsregister(daten_personen)

        wohnsitz_daten = lade_wohnsitzregister()
        wohnsitz_daten.append(neuer_eintrag)
        speichere_wohnsitzregister(wohnsitz_daten)

        datum_heute = date.today().strftime("%d.%m.%Y")

        # ab hier erzeugen wir mit dem Modul fPDF die jeweilige PDF für den Bürger
        logo_path = os.path.join(settings.BASE_DIR, "static", "Logo.png")

        pdf = FPDF()
        pdf_base(pdf, "Meldebestätigung", logo_path=logo_path)

        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, "Hiermit wird bestätigt, dass", ln=True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, f"{person.get('vorname','')} {person.get('nachname_geburt','')}", ln=True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, f"am {datum_heute} seinen Wohnsitz an folgender Adresse angemeldet hat:")
        pdf.ln(4)

        pdf.set_x(25)
        pdf.multi_cell(
            0, 8,
            f"{bestehende_adresse['straße_hausnummer'].replace('_',' ')}\n"
            f"{bestehende_adresse['plz_ort'].replace('_',' ')}\n"
            f"{bestehende_adresse['land']}"
        )
        pdf.set_x(10)
        pdf.ln(6)

        pdf_meta_block(pdf, [
            f"Bürger-ID: {buerger_id}",
            f"Meldungsvorgang-ID: {neuer_eintrag['meldungsvorgang_id']}",
        ])

        pdf_meldebestaetigung = pdf.output(dest="S").encode("latin-1")
        dateiname = f"meldebestaetigung_{date.today().isoformat()}_{neuer_eintrag['meldungsvorgang_id']}.pdf"
        dokument_speichern(buerger_id, "meldebestaetigung", pdf_meldebestaetigung, dateiname)
        response = HttpResponse(pdf_meldebestaetigung, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="meldebestaetigung.pdf"'
        return response

    # -----------------------------------------------------------------------
    # Formular Hochzeit (UMGEBAUT: PDF signieren statt XML signieren)
    # -----------------------------------------------------------------------
    elif vorgang == "standesamt":

        if role != "mitarbeiter" or request.session.get("mitarbeiter_rolle") != "standesamt":
            return render(request, "einwohnermeldeamt/buerger_services.html", {
                "adressen": adressen,
                "error": "Keine Berechtigung für Standesamt."
            })

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

        datum_heute = date.today().strftime("%d.%m.%Y")
        datum_ehe = eheschliessungsdatum
        try:
            if eheschliessungsdatum:
                jahr, monat, tag = eheschliessungsdatum.split("-")
                datum_ehe = f"{tag}.{monat}.{jahr}"
        except Exception:
            # Falls irgendwas schiefgeht, einfach Originalstring lassen
            pass

        urkundennummer = str(uuid.uuid4())
        name1 = f"{person1.get('vorname','')} {person1.get('nachname_geburt','')}"
        name2_geburtsname = f"{person2.get('vorname','')} {person2.get('nachname_geburt','')}"

        # Aussteller (Mitarbeiter Standesamt) ermitteln
        aussteller_id = request.session.get("user_id")

        aussteller_person = None
        for p in daten_personen:
            if p.get("buerger_id") == aussteller_id:
                aussteller_person = p
                break

        if aussteller_person:
            aussteller_name = f"{aussteller_person.get('vorname','')} {aussteller_person.get('nachname_geburt','')}".strip()
        else:
            aussteller_name = "Unbekannt"

        # -------------------------------------------------------------------
        # 1) PDF erzeugen (wie gehabt)
        # -------------------------------------------------------------------
        logo_path = os.path.join(settings.BASE_DIR, "static", "Logo.png")

        pdf = FPDF()
        pdf_base(pdf, "Heiratsurkunde", logo_path=logo_path)

        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, f"Urkundennummer: {urkundennummer}", ln=True)
        pdf.ln(2)

        pdf.multi_cell(0, 8, f"Am {datum_ehe} wurde die Ehe geschlossen zwischen")
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, name1, ln=True)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, "und", ln=True)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, name2_geburtsname, ln=True)
        pdf.ln(4)

        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, f"Die Person mit der Buerger-ID {b_id_2} fuehrt ab Eheschliessung den Familiennamen:")
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, neuerNachname, ln=True)
        pdf.ln(6)

        # Hinweis: Template soll weiter funktionieren -> wir behalten „signatur_datei“ als Feld im Register
        # (aber es ist jetzt eine signierte PDF, keine XML)
        sig_filename_preview = f"heiratsurkunde_{urkundennummer}.signed.pdf"

        pdf_meta_block(pdf, [
            f"Eintrag im Personenstandsregister vom {datum_heute}.",
            f"Ausgestellt von: {aussteller_name} (Standesamt)",
            f"E-Signatur: eingebettet in PDF ({sig_filename_preview})",
        ])

        # >>> sichtbarer Signatur-Text GANZ UNTEN (optional, rein informativ)
        pdf.set_text_color(80, 80, 80)
        pdf.set_font("Helvetica", "", 9)
        pdf.ln(14)
        pdf.multi_cell(0, 5, f"Elektronisch signiert durch {aussteller_name}. Signatur-ID: {urkundennummer}")

        pdf_hochzeit_unsigned = pdf.output(dest="S").encode("latin-1")

        # -------------------------------------------------------------------
        # 2) PDF signieren (NEU)
        # -------------------------------------------------------------------
        try:
            sign_info = signiere_heiratsurkunde_pdf(
                urkundennummer=urkundennummer,
                pdf_bytes=pdf_hochzeit_unsigned,
                aussteller_name=aussteller_name,
            )
        except Exception as e:
            return render(request, "einwohnermeldeamt/buerger_services.html", {
                "adressen": adressen,
                "error": f"PDF-Signatur fehlgeschlagen: {str(e)}"
            })

        pdf_hochzeit_signed = sign_info["signed_pdf_bytes"]
        sig_filename = sign_info["sig_filename"]

        # -------------------------------------------------------------------
        # 3) Signierte PDF speichern (Bürger bekommt signierte PDF)
        # -------------------------------------------------------------------
        dateiname = f"heiratsurkunde_{date.today().isoformat()}_{urkundennummer}.pdf"

        doc_id_1 = dokument_speichern(b_id_1, "heiratsurkunde", pdf_hochzeit_signed, dateiname)
        doc_id_2 = dokument_speichern(b_id_2, "heiratsurkunde", pdf_hochzeit_signed, dateiname)

        # >>> Signatur-Info im Dokumentenregister vermerken (Template-Button bleibt damit sichtbar)
        docs = lade_dokumentenregister()
        for d in docs:
            if d.get("doc_id") in (doc_id_1, doc_id_2):
                # Feldname bleibt gleich -> dokumente.html muss nicht zwingend angepasst werden
                d["signatur_datei"] = sig_filename  # jetzt: *.signed.pdf (Kopie im Signaturen-Ordner)
                d["signatur_typ"] = "pdf"
        speichere_dokumentenregister(docs)

        response = HttpResponse(pdf_hochzeit_signed, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="heiratsurkunde.pdf"'
        return response

    return HttpResponse("method_not_allowed", status=405, content_type="text/plain")


# ---------------------------------------------------------------------------
# (ALT) verify_heiratsurkunde_signatur per XML -> (NEU) per signierter PDF
# Wir lassen den Endpoint bestehen, damit URLs/Tests nicht brechen.
# Erwartet urkunden_id und prüft /var/www/django-project/signaturen/heiratsurkunde_<id>.signed.pdf
# ---------------------------------------------------------------------------

@require_GET
def verify_heiratsurkunde_signatur(request, urkunden_id):
    if not request.session.get("user_id"):
        return redirect("login")

    # optional: nur Mitarbeiter Standesamt dürfen verifizieren
    if request.session.get("role") != "mitarbeiter" or request.session.get("mitarbeiter_rolle") != "standesamt":
        return HttpResponse("Keine Berechtigung", status=403)

    pdf_path = f"/var/www/django-project/signaturen/heiratsurkunde_{urkunden_id}.signed.pdf"
    if not os.path.exists(pdf_path):
        return HttpResponse("Signierte PDF nicht gefunden", status=404)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result = verify_pdf_signatur_bytes(pdf_bytes=pdf_bytes)

    # Für Debug: JSON ausgeben (statt XML)
    return JsonResponse(result, status=200 if result.get("ok") else 400)


# ---------------------------------------------------------------------------
# Signaturprüfung aus dem Dokumentenbereich (Button in dokumente.html)
# -> prüft die eingebettete Signatur der PDF-Datei selbst.
# Templates funktionieren weiter, weil wir signatur_datei weiter setzen.
# ---------------------------------------------------------------------------

@require_GET
def signatur_pruefen(request, doc_id):
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
        return JsonResponse({"ok": False, "error": "Dokument nicht gefunden"}, status=404)

    # Template hängt evtl. an signatur_datei -> wir behalten das Feld,
    # aber für die Prüfung brauchen wir die PDF selbst.
    if not doc.get("signatur_datei"):
        return JsonResponse({"ok": False, "error": "Keine Signatur hinterlegt"}, status=400)

    dateiname = doc.get("dateiname")
    if not dateiname:
        return JsonResponse({"ok": False, "error": "Dokument hat keinen Dateinamen im Register"}, status=500)

    # DOKU_BASE wird bei euch global definiert (wie in views.py oben)
    pdf_path = os.path.join(DOKU_BASE, buerger_id, dateiname)
    if not os.path.exists(pdf_path):
        return JsonResponse({"ok": False, "error": "PDF-Datei nicht gefunden"}, status=404)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result = verify_pdf_signatur_bytes(pdf_bytes=pdf_bytes)

    if result.get("ok"):
        return JsonResponse({
            "ok": True,
            "message": result.get("message", "Signatur gueltig"),
            "signatur_datei": doc.get("signatur_datei"),
            "signatur_typ": doc.get("signatur_typ", "pdf"),
        })

    return JsonResponse({
        "ok": False,
        "error": result.get("message", "Signatur ungueltig"),
        "detail": result.get("detail", ""),
        "signatur_datei": doc.get("signatur_datei"),
        "signatur_typ": doc.get("signatur_typ", "pdf"),
    }, status=400)


    
    
@require_GET
def dokumente(request):
    if not request.session.get("user_id"):
        return redirect("login")

    buerger_id = request.session.get("user_id")

    docs = lade_dokumentenregister()
    docs = [d for d in docs if d.get("buerger_id") == buerger_id]

    for d in docs:
        ca = d.get("created_at")
        if isinstance(ca, str) and ca:
            try:
                d["created_at_dt"] = dt.datetime.fromisoformat(ca)
            except ValueError:
                d["created_at_dt"] = None
        else:
            d["created_at_dt"] = None

    docs.sort(key=lambda x: x.get("created_at_dt") or dt.datetime.min, reverse=True)

    return render(request, "einwohnermeldeamt/dokumente.html", {"docs": docs})




#API zwischen Personenstands-Register und Ressort Gesundheit&Soziales & Steuern&Bank

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
            try:
                uuid.UUID(vater_id)
                uuid.UUID(mutter_id)
            except ValueError:
                return HttpResponse("invalid_parent_uuid", status=400, content_type="text/plain")

            
            for person in daten:       #Eltern im Personenstands-Register suchen
                if person.get("buerger_id") == vater_id:
                    vater_person = person
                if person.get("buerger_id") == mutter_id:
                    mutter_person = person
                    
            if not vater_person or not mutter_person:
                return JsonResponse({"error": "eltern nicht gefunden", "vater_gefunden": bool(vater_person), "mutter_gefunden": bool(mutter_person)}, status=400)
            #if not vater_person or not mutter_person:
                #return HttpResponse("parents_not_found", status=400, content_type="text/plain")

        
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
        #erweitern um Immigration (ausgesetzt)
        
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
            "p1": erstelle_neuen_eintrag["vater_id"],
            "p2": erstelle_neuen_eintrag["mutter_id"],
        }  
            
        meldung_data = requests.post(url_steuern_bank, data = meldung_data, timeout=5)


        return HttpResponse(erstelle_neuen_eintrag["buerger_id"], status=201, content_type="text/plain") # generierte buerger_id als HTTP zurückgeben an Gesundheit&Soziales (PDF als Geburtsurkunde)


    return HttpResponse("method_not_allowed", status=405, content_type="text/plain")



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



#Hier zwei Funktion zum Aktivieren und Deaktivieren des Mitarbeiter_Modus

@csrf_exempt
def mitarbeiter_enable(request):
    if not request.session.get("user_id"):
        return redirect("login")

    if request.method != "POST":
        return redirect("buerger_services")

    buerger_id = request.session["user_id"]
    pin = request.POST.get("pin", "")

    m = pruefe_mitarbeiter_pin(buerger_id, pin)
    if not m:
        request.session["error"] = "PIN ungültig oder keine Mitarbeiter-Berechtigung."
        return redirect("buerger_services")

    request.session["role"] = "mitarbeiter"
    request.session["mitarbeiter_rolle"] = m.get("rolle")

    return redirect("buerger_services")



def mitarbeiter_disable(request):
    if not request.session.get("user_id"):
        return redirect("login")

    request.session["role"] = "buerger"
    request.session.pop("mitarbeiter_rolle", None)
    return redirect("buerger_services")












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


TARGET_URL_RECHT_ORDNUNG = "http://[2001:7c0:2320:2:f816:3eff:fe79:999d]" #Zieladresse von Ressort "Recht & Ordnung, Port 80

def weiterleiten_recht_ordnung(request):
    buerger_id = request.session.get("user_id")
    if not buerger_id:
        return HttpResponse("Nicht eingeloggt!", status=401)

    token = create_jwt(buerger_id)
    redirect_url = f"{TARGET_URL_RECHT_ORDNUNG}/ro/jwt-login?token={quote(token)}"
    return redirect(redirect_url) 


TARGET_URL_GESUNDHEITSAMTSAMT = "http://[2001:7c0:2320:2:f816:3eff:fe06:8d56]:8000" #Zieladresse von Teil-Ressort "Gesundheits-Amt"

def weiterleiten_gesundheitsamt(request):
    buerger_id = request.session.get("user_id")
    if not buerger_id:
        return HttpResponse("Nicht eingeloggt!", status=401)

    token = create_jwt(buerger_id)
    redirect_url = f"{TARGET_URL_GESUNDHEITSAMTSAMT}/jwt-login?token={quote(token)}"
    return redirect(redirect_url) 


TARGET_URL_SOZIALAMT = "http://[2001:7c0:2320:2:f816:3eff:fed4:e456]:1810" #Zieladresse von Teil-Ressort "Sozial-Amt"

def weiterleiten_sozialamt(request):
    buerger_id = request.session.get("user_id")
    if not buerger_id:
        return HttpResponse("Nicht eingeloggt!", status=401)

    token = create_jwt(buerger_id)
    redirect_url = f"{TARGET_URL_SOZIALAMT}/jwt-login?token={quote(token)}"
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
    setze_session_namen(request, buerger_id) #diese Zeile haben wir neu gesetzt
    request.session["role"] = "buerger"             #neu gesetzt für unsere rollen in Ressort Meldewesen
    request.session.pop("mitarbeiter_rolle", None)  #neu gesetzt für unsere rollen in Ressort Meldewesen


    # Weiter ins Dashboard
    return redirect("mainpage") #hier anpassen, weiterleiten auf die Zielseite





