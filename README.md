# LeadRadar Bremen – Setup & Bedienung

## Was ist das?
Ein lokales Lead-Intelligence-Dashboard für Baufinanzierungsberater.
Läuft komplett auf deinem Computer – keine Cloud, keine monatlichen Kosten.

---

## Schnellstart (5 Minuten)

### 1. Python installieren
Falls nicht vorhanden: https://www.python.org/downloads/
(Python 3.10 oder neuer)

### 2. Abhängigkeiten installieren
Öffne ein Terminal im LeadRadar-Ordner:
```
pip install -r requirements.txt
```

### 3. Datenbank initialisieren + Server starten
```
python app.py
```
→ Dashboard öffnet sich unter: http://localhost:5000

### 4. Scraper einmalig alle ausführen (erster Lauf)
In einem zweiten Terminal-Fenster:
```
python scheduler.py --now
```

### 5. Automatischen Scheduler starten (dauerhaft)
```
python scheduler.py
```
Scraper laufen jetzt automatisch täglich/stündlich.

---

## Tägliche Nutzung

1. `python app.py` starten
2. Browser öffnen: http://localhost:5000
3. Dashboard zeigt alle aktuellen Leads
4. KI-Lead-Scorer: Texte reinkopieren → sofort analysiert

---

## Wettbewerber anpassen

Öffne `scrapers/wettbewerber.py` und passe die `WETTBEWERBER`-Liste an:
```python
WETTBEWERBER = [
    {'name': 'Name des Konkurrenten', 'google_search': '...'},
    ...
]
```

---

## Datenbank direkt ansehen (optional)

Mit DB Browser for SQLite (kostenlos): https://sqlitebrowser.org/
→ Datei: `data/leads.db` öffnen

---

## Auf einem Server deployen (optional, für 24/7-Betrieb)

Empfohlen: Railway.app (ca. 5€/Monat)
1. Account erstellen auf railway.app
2. GitHub-Repo anlegen und Code hochladen
3. Bei Railway: "New Project from GitHub" → App wird automatisch deployed
4. Umgebungsvariable setzen: PORT=5000

---

## Bekannte Einschränkungen

- Einige Webseiten blockieren gelegentlich Scraping → Scraper läuft dann leer
- Handelsregister.de erfordert manchmal CAPTCHA → manueller Besuch nötig
- Immowelt/ImmoScout: nur öffentliche Daten (kein Account-Scraping)

---

## Support
Bei Fragen: Öffne einfach das Dashboard und nutze den KI-Chat.
