import uuid
import json
import requests
import time
import datetime as date
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from pathlib import Path                            #funktioniert PLattform-übergreifend






# Pfade zu den Registern
personenstandsregister = Path("db/personenstandsregister.json")




def lade_personenstandsregister():
    if not personenstandsregister.exists():
        return []
    try:
        with open(personenstandsregister, "r", encoding="utf-8") as datei:
            daten = json.load(datei)
            if isinstance(daten, dict):
                return []
            return daten
    except json.JSONDecodeError:
        return []
    


def erzeuge_public_key():
    pass

def erzeuge_buerger_id():
    pass



