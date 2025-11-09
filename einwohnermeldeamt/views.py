import uuid
import json
import requests
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
        with open(personenstandsregister, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict):
                return []
            return data
    except json.JSONDecodeError:
        return []