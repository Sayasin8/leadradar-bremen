# LeadRadar Bremen – Cloud Deployment Anleitung

---

## WEG A: Strato V-Server (falls du einen hast – kostenlos!)

Falls du unter strato.de einen **V-Server** oder **Managed Server** hast,
brauchst du Railway nicht. Prüfe das zuerst in deinem Strato-Kundencenter.

### Schritt 1 – SSH-Zugang prüfen
Strato schickt dir beim V-Server eine IP-Adresse und Root-Passwort per E-Mail.
Falls du das hast: Weiter mit Schritt 2.
Falls nicht (normales Webhosting): → Gehe zu Weg B (Railway).

### Schritt 2 – Mit dem Server verbinden
Windows: Lade "PuTTY" herunter (kostenlos) von putty.org
Mac/Linux: Terminal öffnen

```
ssh root@DEINE-IP-ADRESSE
```
Passwort eingeben (aus der Strato-E-Mail).

### Schritt 3 – Python & Abhängigkeiten installieren
```bash
apt update && apt upgrade -y
apt install python3 python3-pip git -y
```

### Schritt 4 – LeadRadar hochladen
Auf deinem Computer: ZIP-Datei entpacken.
Dann im Terminal (auf deinem Computer, nicht Server):
```bash
scp -r leadradar/ root@DEINE-IP:/opt/leadradar
```

### Schritt 5 – Dependencies installieren
```bash
cd /opt/leadradar
pip3 install -r requirements.txt
```

### Schritt 6 – App dauerhaft starten (systemd)
```bash
cat > /etc/systemd/system/leadradar.service << EOF
[Unit]
Description=LeadRadar Bremen
After=network.target

[Service]
WorkingDirectory=/opt/leadradar
ExecStart=/usr/bin/python3 app.py
Restart=always
Environment=PORT=5000

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable leadradar
systemctl start leadradar
```

### Schritt 7 – Firewall öffnen
```bash
ufw allow 5000
```

### Fertig!
Dashboard erreichbar unter: http://DEINE-IP:5000

---

## WEG B: Railway.app (kostenlose Alternative, 5 Minuten)

Railway gibt dir 5$ Guthaben pro Monat – für diese App reicht das locker.
Keine Kreditkarte nötig für den Start.

---

### Schritt 1 – GitHub Account erstellen
→ https://github.com
"Sign up" → E-Mail eingeben → Kostenloses Konto

---

### Schritt 2 – LeadRadar auf GitHub hochladen

1. Nach dem Login auf GitHub: Klicke oben rechts auf "+" → "New repository"
2. Name: `leadradar-bremen`
3. Auf "Create repository" klicken
4. Jetzt siehst du Anweisungen. Klicke auf "uploading an existing file"
5. Ziehe ALLE Dateien aus dem entpackten ZIP-Ordner hinein
   (app.py, requirements.txt, Dockerfile, railway.json, static/, scrapers/)
6. Klicke unten auf "Commit changes"

✅ Dein Code ist jetzt auf GitHub.

---

### Schritt 3 – Railway Account erstellen
→ https://railway.app
"Login with GitHub" klicken → GitHub-Zugang erlauben

---

### Schritt 4 – Neues Projekt auf Railway

1. Auf Railway: Klicke "New Project"
2. Wähle "Deploy from GitHub repo"
3. Wähle "leadradar-bremen" aus der Liste
4. Railway erkennt automatisch das Dockerfile
5. Klicke "Deploy Now"

⏳ Railway baut die App jetzt (ca. 2–3 Minuten).

---

### Schritt 5 – Öffentliche URL aktivieren

1. Nach dem Deploy: Klicke auf deinen Service
2. Gehe zum Tab "Settings"
3. Scrolle zu "Networking" → "Generate Domain"
4. Klicke "Generate Domain"

✅ Du bekommst eine URL wie: `leadradar-bremen.up.railway.app`

Das ist dein Dashboard – von überall erreichbar, auch auf dem Handy.

---

### Schritt 6 – Erste Scraper-Ausführung

Öffne deine Railway-URL + /api/scrape/all:
```
https://leadradar-bremen.up.railway.app/api/scrape/all
```
(einfach im Browser öffnen)

Oder: In deinem Dashboard gibt es einen "Alle Scraper starten" Button
(falls du das Frontend entsprechend nutzt).

---

### Schritt 7 – Passwortschutz einrichten (empfohlen)

Damit nicht jeder dein Dashboard sehen kann:

1. Auf Railway → dein Projekt → "Variables" Tab
2. Klicke "New Variable"
3. Name: `DASHBOARD_PASSWORD`, Wert: dein gewünschtes Passwort
4. App wird automatisch neu gestartet

(Ich kann den Passwortschutz auf Wunsch in den Code einbauen)

---

## Kosten-Übersicht

| Option | Kosten | Voraussetzung |
|--------|--------|---------------|
| Strato V-Server | 0€ extra (bereits bezahlt) | V-Server im Strato-Account |
| Railway Free | 0€/Monat | GitHub Account |
| Railway Paid | ~5€/Monat | Mehr als 500h Laufzeit nötig |

---

## Nächste Schritte nach dem Deployment

1. Dashboard öffnen, erste Leads checken
2. Wettbewerber-Liste anpassen (scrapers/wettbewerber.py)
3. Optional: Passwortschutz aktivieren
4. Optional: E-Mail-Alerts bei neuen Hot-Leads einrichten

---

## Hilfe benötigt?

Schreib mir welchen Weg du gehst (Strato V-Server oder Railway)
und ich führe dich Schritt für Schritt durch.
