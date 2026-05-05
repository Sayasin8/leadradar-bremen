"""
Wettbewerber Monitor
Überwacht Google Reviews, ProvenExpert & Trustpilot der lokalen Konkurrenz
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import sqlite3
import json
from scrapers.base import BaseScraper

# Bekannte Wettbewerber in Bremen (manuell anpassbar!)
WETTBEWERBER = [
    {
        'name': 'Interhyp Bremen',
        'google_search': 'Interhyp Bremen Bewertungen',
        'provenexpert': 'https://www.provenexpert.com',
    },
    {
        'name': 'Dr. Klein Bremen',
        'google_search': 'Dr. Klein Baufinanzierung Bremen Bewertung',
        'provenexpert': 'https://www.provenexpert.com',
    },
    {
        'name': 'PlanetHome Bremen',
        'google_search': 'PlanetHome Bremen negative Bewertung',
        'provenexpert': 'https://www.provenexpert.com',
    },
]

NEGATIVE_KEYWORDS = [
    'enttäuscht', 'schlecht', 'katastrophe', 'nie wieder', 'finger weg',
    'warte seit wochen', 'keine rückmeldung', 'abgelehnt', 'unfreundlich',
    'chaotisch', 'fehler', 'inkompetent', 'betrug', 'unzufrieden',
    'schlechte kommunikation', 'nicht empfehlenswert', 'mangelhaft'
]


class WettbewerberScraper(BaseScraper):
    source = 'wett'
    source_label = 'Wettbewerber'

    def run(self):
        self.logger.info("Starte Wettbewerber-Monitor...")
        for wett in WETTBEWERBER:
            self._check_google_reviews(wett)
            self._check_provenexpert(wett)
        self.print_summary()

    def _check_google_reviews(self, wett: dict):
        """Sucht nach negativen Google-Bewertungen via Bing-Suche"""
        query = f"{wett['name']} Bewertung 1 Stern negative Erfahrung 2025"
        url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&setlang=de"

        soup = self.fetch(url)
        if not soup:
            return

        results = soup.find_all(['li', 'div'], class_=re.compile(r'b_algo|result'))
        for result in results[:5]:
            text = result.get_text(separator=' ', strip=True).lower()
            neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

            if neg_count < 1:
                continue

            title_el = result.find(['h2', 'h3', 'a'])
            title = title_el.get_text(strip=True)[:100] if title_el else f'Negative Bewertung: {wett["name"]}'
            link = result.find('a', href=True)
            url_detail = link['href'] if link else ''

            signals = [
                f'{wett["name"]} erhält negative Bewertungen = Kunden aktiv unzufrieden',
                'Kunden suchen Alternative = direktes Zeitfenster für Kontakt',
                f'{neg_count} Negativ-Signale im Review erkannt',
                'Schwächephase des Wettbewerbers: jetzt Marktanteil gewinnen'
            ]
            score = min(92, 65 + (neg_count * 5))

            self.save_lead(
                title=f'Neg. Review: {wett["name"]} – {title[:60]}',
                description=result.get_text(separator=' ', strip=True)[:300],
                location='Bremen · Öffentlich',
                score=score,
                signals=signals,
                outreach=(
                    f'Ich habe gesehen, dass Erfahrungen mit {wett["name"]} '
                    f'enttäuschend waren. Bei mir ist persönliche Beratung kein Versprechen '
                    f'sondern Standard – ich melde mich innerhalb von 24 Stunden.'
                ),
                url=url_detail
            )

    def _check_provenexpert(self, wett: dict):
        """ProvenExpert-Bewertungen checken"""
        # ProvenExpert öffentliche Profile sind zugänglich
        search_url = f"https://www.provenexpert.com/de-de/search/?q={wett['name'].replace(' ', '+')}"
        soup = self.fetch(search_url)
        if not soup:
            return

        profiles = soup.find_all('div', class_=re.compile(r'expert|profile|result'))
        for profile in profiles[:3]:
            text = profile.get_text(strip=True)
            rating_match = re.search(r'(\d[.,]\d)\s*(?:von|/)\s*5', text)
            if not rating_match:
                continue

            rating = float(rating_match.group(1).replace(',', '.'))
            if rating >= 4.0:
                continue  # Gut bewerteter Wettbewerber – ignorieren

            signals = [
                f'{wett["name"]} ProvenExpert-Score: {rating}/5.0',
                'Niedriger Score = strukturelle Schwäche, nicht Einzelfall',
                'Kunden bereit für Wechsel zu besserem Berater',
            ]

            self.save_lead(
                title=f'ProvenExpert-Schwäche: {wett["name"]} ({rating}/5.0)',
                description=text[:300],
                location='Bremen',
                score=75 if rating < 3.0 else 62,
                signals=signals,
                outreach=(
                    f'Unzufriedene Kunden von {wett["name"]} brauchen eine Alternative. '
                    f'Mit meinem Ansatz – persönlich, schnell, transparent – '
                    f'bin ich das Gegenteil dessen, was sie erlebt haben.'
                ),
                url=search_url
            )


# ──────────────────────────────────────────────────────


class SchwarzesBrettScraper(BaseScraper):
    """Schwarzes Brett Scraper"""
    source = 'brett'
    source_label = 'Schwarzes Brett'

    URLS = [
        'https://www.schwarzesbrett.de/immobilien-gesuche/suche.html?ort=Bremen&radius=50',
        'https://www.quoka.de/immobilien/gesuche/?region=bremen',
    ]

    def run(self):
        self.logger.info("Starte Schwarzes-Brett-Scraper...")
        for url in self.URLS:
            self._scrape_url(url)
        self.print_summary()

    def _scrape_url(self, url: str):
        soup = self.fetch(url)
        if not soup:
            return

        ads = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'ad|listing|entry|result'))
        for ad in ads[:15]:
            title_el = ad.find(['h2', 'h3', 'a'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            text = ad.get_text(separator=' ', strip=True)
            text_l = text.lower()

            if not any(kw in text_l for kw in ['haus', 'wohnung', 'kaufen', 'suche', 'gesucht']):
                continue

            link_el = ad.find('a', href=True)
            ad_url = ''
            if link_el:
                href = link_el['href']
                ad_url = href if href.startswith('http') else 'https://www.schwarzesbrett.de' + href

            signals = []
            if 'familie' in text_l or 'kinder' in text_l:
                signals.append('Familie mit Kindern = KfW-Familienbonus möglich')
            if 'festangestellt' in text_l or 'angestellt' in text_l:
                signals.append('Festanstellung erwähnt = sichere Bonität')
            if any(c in text_l for c in ['€', 'budget', 'preis']):
                signals.append('Preisvorstellung klar – realistische Kaufabsicht')
            signals.append('Aktive Kaufsuche über Schwarzes Brett = Nicht-digitale Zielgruppe')

            score = self.score_lead(signals, base=50)

            self.save_lead(
                title=title[:120],
                description=text[:300],
                location='Bremen Region',
                score=score,
                signals=signals,
                outreach=(
                    'Ihre Anzeige zeigt, dass Sie konkret auf der Suche sind. '
                    'Ich helfe Ihnen als spezialisierter Baufinanzierungsberater '
                    'dabei, die passende Finanzierung zu finden.'
                ),
                url=ad_url
            )


# ──────────────────────────────────────────────────────


class MietpreisScraper(BaseScraper):
    """Mietpreis vs. Kaufrate Berechnung per PLZ"""
    source = 'miete'
    source_label = 'Mietpreis-Radar'

    # Echte Richtwerte für Bremen-Region (aus Marktdaten)
    MIET_DATA = [
        {'plz': '28195', 'area': 'Bremen Mitte',     'miete_3zi': 1580, 'kaufpreis_m2': 3800},
        {'plz': '28199', 'area': 'Neustadt',         'miete_3zi': 1450, 'kaufpreis_m2': 3600},
        {'plz': '28203', 'area': 'Steintor',         'miete_3zi': 1520, 'kaufpreis_m2': 3750},
        {'plz': '28205', 'area': 'Östliche Vorstadt','miete_3zi': 1600, 'kaufpreis_m2': 3900},
        {'plz': '28209', 'area': 'Schwachhausen',    'miete_3zi': 1750, 'kaufpreis_m2': 4200},
        {'plz': '28215', 'area': 'Findorff',         'miete_3zi': 1480, 'kaufpreis_m2': 3700},
        {'plz': '28277', 'area': 'Obervieland',      'miete_3zi': 1380, 'kaufpreis_m2': 3200},
        {'plz': '28279', 'area': 'Huchting',         'miete_3zi': 1300, 'kaufpreis_m2': 2900},
        {'plz': '28307', 'area': 'Hemelingen',       'miete_3zi': 1420, 'kaufpreis_m2': 3100},
        {'plz': '28329', 'area': 'Vahr',             'miete_3zi': 1350, 'kaufpreis_m2': 2950},
        {'plz': '28355', 'area': 'Horn',             'miete_3zi': 1460, 'kaufpreis_m2': 3300},
        {'plz': '28359', 'area': 'Horn-Lehe',        'miete_3zi': 1680, 'kaufpreis_m2': 3850},
        {'plz': '27749', 'area': 'Delmenhorst',      'miete_3zi': 1180, 'kaufpreis_m2': 2400},
        {'plz': '28816', 'area': 'Stuhr',            'miete_3zi': 1520, 'kaufpreis_m2': 3350},
        {'plz': '28832', 'area': 'Achim',            'miete_3zi': 1450, 'kaufpreis_m2': 3100},
        {'plz': '28876', 'area': 'Oyten',            'miete_3zi': 1390, 'kaufpreis_m2': 2850},
        {'plz': '27283', 'area': 'Verden',           'miete_3zi': 1220, 'kaufpreis_m2': 2600},
        {'plz': '26122', 'area': 'Oldenburg',        'miete_3zi': 1380, 'kaufpreis_m2': 3000},
        {'plz': '28717', 'area': 'Vegesack',         'miete_3zi': 1350, 'kaufpreis_m2': 3200},
    ]

    def run(self):
        self.logger.info("Berechne Mietpreis-Schmerzpunkte...")
        self._calc_and_store()
        self._create_leads_for_alerts()
        self.print_summary()

    def _calc_kauf_rate(self, kaufpreis_m2: float, qm: float = 90) -> float:
        """Berechnet ungefähre Monatsrate (3,5%, 25J, 80% Beleihung)"""
        kaufpreis = kaufpreis_m2 * qm
        darlehen = kaufpreis * 0.80
        zins = 0.035 / 12
        n = 25 * 12
        rate = darlehen * (zins * (1 + zins) ** n) / ((1 + zins) ** n - 1)
        nebenkosten = kaufpreis * 0.12 / 12 / 12  # Grundsteuer, Instandhaltung
        return round(rate + nebenkosten)

    def _calc_and_store(self):
        conn = sqlite3.connect('data/leads.db')
        for item in self.MIET_DATA:
            rate = self._calc_kauf_rate(item['kaufpreis_m2'])
            conn.execute('''
                INSERT OR REPLACE INTO mietpreis (plz, area, miete_avg, kauf_rate_avg)
                VALUES (?, ?, ?, ?)
            ''', [item['plz'], item['area'], item['miete_3zi'], rate])
        conn.commit()
        conn.close()
        self.logger.info(f"{len(self.MIET_DATA)} PLZ-Datenpunkte gespeichert.")

    def _create_leads_for_alerts(self):
        """Erstellt Leads für PLZ wo Miete > Kaufrate"""
        conn = sqlite3.connect('data/leads.db')
        alerts = conn.execute(
            'SELECT * FROM mietpreis WHERE miete_avg > kauf_rate_avg'
        ).fetchall()
        conn.close()

        for row in alerts:
            row = dict(row)
            diff = int(row['miete_avg'] - row['kauf_rate_avg'])
            jahres_diff = diff * 12

            signals = [
                f'Ø Miete 3-Zimmer: {int(row["miete_avg"])}€/Monat',
                f'Ø Kaufrate gleiche Größe: {int(row["kauf_rate_avg"])}€/Monat',
                f'Ersparnis durch Kauf: {diff}€/Monat = {jahres_diff}€/Jahr',
                'Mathematisch unschlagbares Kaufargument für alle Mieter in diesem PLZ',
            ]

            self.save_lead(
                title=f'Mietpreis-Alert: {row["area"]} ({row["plz"]}) – Kaufen {diff}€/Monat günstiger',
                description=(
                    f'In PLZ {row["plz"]} ({row["area"]}) kostet Mieten durchschnittlich '
                    f'{int(row["miete_avg"])}€/Monat für eine 3-Zimmer-Wohnung. '
                    f'Die Monatsrate für eine Eigentumswohnung gleicher Größe liegt bei '
                    f'ca. {int(row["kauf_rate_avg"])}€. Das ergibt eine Ersparnis von '
                    f'{diff}€/Monat = {jahres_diff}€ pro Jahr.'
                ),
                location=f'{row["area"]} · {row["plz"]}',
                plz=row['plz'],
                score=70 + min(20, diff // 20),
                signals=signals,
                outreach=(
                    f'Wussten Sie, dass Sie in {row["area"]} monatlich {diff}€ sparen könnten, '
                    f'wenn Sie kaufen statt mieten? Ich rechne das individuell für Sie durch – '
                    f'kostenlos und ohne Verpflichtung.'
                ),
                url=f'https://leadradar.local/mietpreis/{row["plz"]}'
            )


if __name__ == '__main__':
    import sys
    if 'wett' in sys.argv[0] or __name__ == '__main__':
        WettbewerberScraper().run()
    SchwarzesBrettScraper().run()
    MietpreisScraper().run()
