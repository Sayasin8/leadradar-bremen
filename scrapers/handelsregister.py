"""
Handelsregister Scraper
Quelle: handelsregister.de (öffentlich zugänglich)
Ziel: Neugründungen, Kapitalerhöhungen, Umzüge in der Region Bremen
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import urllib.parse
from scrapers.base import BaseScraper, REGION_CITIES

HIGH_KAUFKRAFT_BERUFE = [
    'arzt', 'ärztin', 'zahnarzt', 'apotheke', 'rechtsanwalt', 'notar',
    'steuerberater', 'unternehmensberater', 'it', 'software', 'tech',
    'ingenieur', 'architekt', 'finanz', 'immobilien'
]


class HandelsregisterScraper(BaseScraper):
    source = 'handel'
    source_label = 'Handelsregister'

    BASE_URL = 'https://www.handelsregister.de/rp_web/ergebnis.xhtml'

    def run(self):
        self.logger.info("Starte Handelsregister-Scraper...")
        for city in REGION_CITIES[:8]:
            self._search_city(city)
        self.print_summary()

    def _search_city(self, city: str):
        """Sucht Neugründungen in einer Stadt"""
        params = {
            'schlagwoerter': city,
            'schlagwoerterOption': 'AND',
            'bundesland': 'HB',
            'registerArt': 'HRB',
            'zeitraum': '30',  # letzte 30 Tage
        }
        soup = self.fetch(self.BASE_URL, params=params)
        if not soup:
            return

        rows = soup.find_all('tr', class_=re.compile(r'row|result|entry'))
        if not rows:
            # Versuche Tabellenzeilen direkt
            rows = soup.find_all('tr')[1:21]

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            name = cells[0].get_text(strip=True)
            rechtsform = cells[1].get_text(strip=True) if len(cells) > 1 else ''
            ort = cells[2].get_text(strip=True) if len(cells) > 2 else city
            status = cells[-1].get_text(strip=True) if cells else ''

            if not name or len(name) < 3:
                continue

            # Nur relevante Events
            if not any(kw in status.lower() for kw in ['neueintragung', 'kapital', 'sitzverlegung', 'eintragung']):
                if 'neueintragung' not in ' '.join([c.get_text() for c in cells]).lower():
                    continue

            signals = self._build_signals(name, rechtsform, status, ort)
            score = self.score_lead(signals, base=58)
            outreach = self._build_outreach(name, rechtsform, signals)

            url_link = ''
            link_el = row.find('a', href=True)
            if link_el:
                href = link_el['href']
                url_link = href if href.startswith('http') else 'https://www.handelsregister.de' + href

            self.save_lead(
                title=f'{rechtsform}-Gründung: {name[:60]} – {ort}',
                description=f'Neuer Handelsregistereintrag. Rechtsform: {rechtsform}. Ort: {ort}.',
                location=ort,
                score=score,
                signals=signals,
                outreach=outreach,
                url=url_link or self.BASE_URL
            )

    def _build_signals(self, name: str, rechtsform: str, status: str, ort: str) -> list:
        signals = []
        name_l = name.lower()

        # Branche aus Firmenname ableiten
        for beruf in HIGH_KAUFKRAFT_BERUFE:
            if beruf in name_l:
                signals.append(f'Branche {beruf.title()} = sehr gutes Kreditprofil')
                break

        if 'gmbh' in rechtsform.lower():
            signals.append('GmbH-Gründung = Unternehmerhaushalt mit Eigenkapital')
        elif 'ug' in rechtsform.lower():
            signals.append('UG-Gründung = Einstieg in Selbstständigkeit')
        elif 'einzelunternehmen' in rechtsform.lower() or 'e.k' in rechtsform.lower():
            signals.append('Einzelunternehmer = persönliche Bonität relevant')

        if 'kapitalerhöhung' in status.lower():
            signals.append('Kapitalerhöhung = Liquiditätsereignis, Kaufkraft gestiegen')
        elif 'sitzverlegung' in status.lower():
            signals.append('Sitzverlegung nach ' + ort + ' = Umzug der Inhaberin/des Inhabers')
        elif 'neueintragung' in status.lower() or not status:
            signals.append('Neugründung = neuer Lebensmittelpunkt in der Region')

        signals.append('Noch kein Baufinanzierungsberater kontaktiert (frisch eingetragen)')
        return signals

    def _build_outreach(self, name: str, rechtsform: str, signals: list) -> str:
        if 'kapitalerhöhung' in ' '.join(signals).lower():
            return (f'Eine Kapitalerhöhung bei {name} signalisiert Wachstum – ein guter Moment '
                    'auch für private Investitionen. Als Unternehmer haben Sie besondere '
                    'Finanzierungsoptionen beim Immobilienkauf, die ich Ihnen gerne vorstelle.')
        if 'sitzverlegung' in ' '.join(signals).lower():
            return (f'Zur Verlagerung von {name} in unsere Region herzlichen Glückwunsch! '
                    'Bei einem Unternehmensumzug lohnt es sich oft, auch das private Wohnen '
                    'neu zu denken. Ich zeige Ihnen, was aktuell möglich ist.')
        return (f'Zur Gründung von {name} herzlichen Glückwunsch! Viele Gründer unterschätzen, '
                'wie attraktiv Baufinanzierung parallel zum Unternehmensstart sein kann. '
                'Ich erstelle Ihnen unverbindlich ein Konzept.')


if __name__ == '__main__':
    HandelsregisterScraper().run()
