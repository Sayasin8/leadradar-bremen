"""
WG-Gesucht.de Scraper
Ziel: Ausziehende Personen 25–38 Jahre mit festem Einkommen
      = heißeste Käuferdemografie Deutschlands
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from scrapers.base import BaseScraper

REGION_IDS = {
    'Bremen':       '12',
    'Delmenhorst':  '12',  # über Bremen-Umgebung
    'Oldenburg':    '49',
    'Bremerhaven':  '12',
}

HIGH_VALUE_JOBS = [
    'ingenieur', 'arzt', 'ärztin', 'anwalt', 'beamte', 'lehrer',
    'it', 'software', 'entwickler', 'manager', 'consultant',
    'airbus', 'siemens', 'mercedes', 'daimler', 'boeing',
    'krankenpfleger', 'pflegerin', 'apotheker', 'steuerberater',
    'architekt', 'rechtsanwalt'
]

BEAMTEN_KEYWORDS = [
    'lehrer', 'lehrerin', 'beamte', 'beamtin', 'polizei', 'staatsanwalt',
    'richter', 'finanzamt', 'bundeswehr'
]


class WGGesuchtScraper(BaseScraper):
    source = 'wg'
    source_label = 'WG-Gesucht'

    BASE_URL = 'https://www.wg-gesucht.de/wg-zimmer-in-Bremen.12.0.1.0.html'

    def run(self):
        self.logger.info("Starte WG-Gesucht-Scraper...")
        for page in range(0, 3):
            self._scrape_page(page)
        self.print_summary()

    def _scrape_page(self, page: int):
        url = f'https://www.wg-gesucht.de/wg-zimmer-in-Bremen.12.0.1.{page}.html'
        soup = self.fetch(url)
        if not soup:
            return

        # Suchende Personen (nicht anbietende WGs)
        ads = soup.find_all(['div', 'article'], class_=re.compile(r'wgg-card|offer|listing'))
        if not ads:
            ads = soup.find_all('tr', class_=re.compile(r'listenansicht|offer'))

        for ad in ads[:20]:
            self._process_ad(ad)

    def _process_ad(self, element):
        text = element.get_text(separator=' ', strip=True)
        if len(text) < 30:
            return

        # Altersfilter 24–40
        age_match = re.search(r'\b(2[4-9]|3[0-9]|40)\s*(Jahre|J\.|j\.)', text, re.I)
        age = int(age_match.group(1)) if age_match else None

        # Unter 24 = wahrscheinlich Student, nicht relevant
        if age is not None and age < 24:
            self.skipped += 1
            return

        # Muss Beruf oder Einkommen erwähnen
        text_lower = text.lower()
        has_job = any(job in text_lower for job in HIGH_VALUE_JOBS + ['angestellt', 'vollzeit', 'festangestellt'])

        title_el = element.find(['h2', 'h3', 'h4', 'a', 'strong'])
        title = title_el.get_text(strip=True)[:100] if title_el else 'WG-Gesucht: Ausziehende Person'

        link_el = element.find('a', href=re.compile(r'/wg-zimmer|/wohnung'))
        url = ''
        if link_el:
            href = link_el['href']
            url = href if href.startswith('http') else 'https://www.wg-gesucht.de' + href

        if self.lead_exists(url):
            return

        signals = self._build_signals(text, age, has_job)
        score = self.score_lead(signals, base=48)
        outreach = self._build_outreach(text, age)

        self.save_lead(
            title=title,
            description=text[:350],
            location='Bremen',
            score=score,
            signals=signals,
            outreach=outreach,
            url=url
        )

    def _build_signals(self, text: str, age, has_job: bool) -> list:
        signals = []
        text_l = text.lower()

        if age:
            signals.append(f'{age} Jahre alt = Prime-Buyer-Alter für Erstkauf')
        else:
            signals.append('Ausziehende Person = Vorstufe zur eigenen Wohnung/Haus')

        if any(kw in text_l for kw in BEAMTEN_KEYWORDS):
            signals.append('Verbeamtet = bestes Kreditprofil überhaupt')
        elif has_job:
            job_found = next((j for j in HIGH_VALUE_JOBS if j in text_l), None)
            if job_found:
                signals.append(f'Beruf: {job_found.title()} = sicheres Einkommen und gute Bonität')
            else:
                signals.append('Festangestellt = stabile Einkommenssituation')

        if 'unbefristet' in text_l or 'festangestellt' in text_l:
            signals.append('Unbefristetes Arbeitsverhältnis = Bank-freundliches Profil')

        if any(w in text_l for w in ['airbus', 'siemens', 'daimler', 'mercedes']):
            signals.append('Großkonzern-Mitarbeiter = Top-Arbeitgeber, hohe Bonität')

        if 'budget' in text_l and 'offen' in text_l:
            signals.append('Budget offen = finanzielle Flexibilität signalisiert')

        signals.append('Aktiv auf Wohnungssuche = Kaufüberlegung in 6–18 Monaten wahrscheinlich')
        return signals

    def _build_outreach(self, text: str, age) -> str:
        text_l = text.lower()
        if any(kw in text_l for kw in BEAMTEN_KEYWORDS):
            return (
                'Als Beamtin/Beamter sind Sie für Banken einer der attraktivsten '
                'Kreditnehmer überhaupt – unkündbar, sicheres Einkommen, volle Laufzeit. '
                'Ich zeige Ihnen, was das konkret für Ihre Möglichkeiten bedeutet.'
            )
        if age and age >= 30:
            return (
                f'Mit {age} Jahren und festem Einkommen ist der Schritt ins Eigene '
                'oft näher als gedacht. Häufig ist die Monatsrate für Eigentum geringer '
                'als die Miete – das rechne ich Ihnen kostenlos durch.'
            )
        return (
            'Der Wechsel aus der WG ist oft der Moment, in dem Menschen ernsthaft über '
            'Eigentum nachdenken. Ich helfe Ihnen herauszufinden, was in Ihrer Situation '
            'möglich ist – unverbindlich und kostenlos.'
        )


if __name__ == '__main__':
    WGGesuchtScraper().run()
