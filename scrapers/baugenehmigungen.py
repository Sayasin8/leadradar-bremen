"""
Baugenehmigungen Scraper
Quellen:
  - bremen.de öffentliche Bekanntmachungen
  - Niedersachsen Bauantragsstellen (öffentlich)
  - Amtsblatt Bremen
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from scrapers.base import BaseScraper, REGION_CITIES

OUTREACH_TPL = (
    "Herzlichen Glückwunsch zur erteilten Baugenehmigung! Als spezialisierter "
    "Baufinanzierungsberater in der Region Bremen helfe ich Ihnen, die optimale "
    "Finanzierungsstruktur zu finden – inklusive KfW-Förderprogrammen, die viele "
    "Eigentümer nicht kennen. Ich erstelle Ihnen unverbindlich ein Finanzierungskonzept."
)

SANIERUNG_OUTREACH = (
    "Bei einer Sanierung in dieser Größenordnung gibt es aktuell KfW-Förderkredite "
    "bis zu 150.000€ zu vergünstigten Konditionen. Ich prüfe kostenlos, welche "
    "Programme für Ihr Vorhaben infrage kommen."
)


class BaugenehmigungScraper(BaseScraper):
    source = 'bau'
    source_label = 'Baugenehmigung'

    def run(self):
        self.logger.info("Starte Baugenehmigungen-Scraper...")
        self._scrape_bremen_bekanntmachungen()
        self._scrape_amtsblatt_bremen()
        self._scrape_niedersachsen_bauantraege()
        self.print_summary()

    def _scrape_bremen_bekanntmachungen(self):
        """bremen.de – öffentliche Baugenehmigungen"""
        url = 'https://www.bremen.de/bauen-und-wohnen/bauen/baugenehmigung'
        soup = self.fetch(url)
        if not soup:
            return

        # Baugenehmigungen werden als PDF-Links oder Textblöcke veröffentlicht
        entries = soup.find_all(['article', 'div'], class_=re.compile(r'entry|content|item'))

        for entry in entries[:20]:
            text = entry.get_text(separator=' ', strip=True)
            if not any(kw in text.lower() for kw in ['baugenehmigung', 'bauantrag', 'neubau', 'umbau']):
                continue

            title = self._extract_title(entry) or 'Baugenehmigung – Bremen'
            location = self._extract_location(text)
            signals = self._build_signals(text)
            score = self.score_lead(signals, base=62)
            outreach = SANIERUNG_OUTREACH if 'sanierung' in text.lower() else OUTREACH_TPL
            url_detail = self._extract_link(entry, 'https://www.bremen.de')

            self.save_lead(
                title=title,
                description=text[:300],
                location=location,
                score=score,
                signals=signals,
                outreach=outreach,
                url=url_detail
            )

    def _scrape_amtsblatt_bremen(self):
        """Amtsblatt Bremen – Baugenehmigungsankündigungen"""
        url = 'https://www.amtsblatt.bremen.de'
        soup = self.fetch(url)
        if not soup:
            return

        links = soup.find_all('a', href=re.compile(r'baugenehmig|bauantrag', re.I))
        for link in links[:10]:
            href = link.get('href', '')
            if not href.startswith('http'):
                href = 'https://www.amtsblatt.bremen.de' + href

            detail_soup = self.fetch(href)
            if not detail_soup:
                continue

            text = detail_soup.get_text(separator=' ', strip=True)
            if len(text) < 50:
                continue

            title = link.get_text(strip=True) or 'Amtsblatt: Baugenehmigung'
            signals = self._build_signals(text)
            score = self.score_lead(signals, base=65)

            self.save_lead(
                title=title[:120],
                description=text[:400],
                location=self._extract_location(text),
                score=score,
                signals=signals,
                outreach=OUTREACH_TPL,
                url=href
            )

    def _scrape_niedersachsen_bauantraege(self):
        """Niedersächsische Städte – öffentliche Baulisten"""
        city_urls = {
            'Delmenhorst': 'https://www.delmenhorst.de/buerger/bauen',
            'Achim':        'https://www.achim.de/bauen-wohnen',
            'Stuhr':        'https://www.gemeinde-stuhr.de/bauen',
            'Oyten':        'https://www.oyten.de/bauen',
            'Verden':       'https://www.verden.de/bauen-wohnen',
        }

        for city, url in city_urls.items():
            soup = self.fetch(url)
            if not soup:
                continue

            text_blocks = soup.find_all(string=re.compile(
                r'baugenehmigung|bauantrag|neubau|umbau|anbau', re.I
            ))

            for block in text_blocks[:5]:
                parent = block.find_parent(['article', 'div', 'li', 'p'])
                if not parent:
                    continue
                full_text = parent.get_text(separator=' ', strip=True)
                if len(full_text) < 30:
                    continue

                signals = self._build_signals(full_text)
                signals.append(f'Öffentliche Baugenehmigung in {city}')
                score = self.score_lead(signals, base=60)

                self.save_lead(
                    title=f'Bauantrag/Genehmigung – {city}',
                    description=full_text[:300],
                    location=city,
                    score=score,
                    signals=signals,
                    outreach=OUTREACH_TPL,
                    url=url
                )

    def _build_signals(self, text: str) -> list:
        text_l = text.lower()
        signals = []
        if 'neubau' in text_l or 'einfamilienhaus' in text_l:
            signals.append('Neubauprojekt = direkter Finanzierungsbedarf')
        if 'doppelhaus' in text_l or 'dhh' in text_l:
            signals.append('Doppelhausprojekt = zwei potenzielle Kreditnehmer')
        if 'mehrfamilienhaus' in text_l or 'mfh' in text_l:
            signals.append('Mehrfamilienhaus = höheres Finanzierungsvolumen')
        if 'sanierung' in text_l or 'umbau' in text_l:
            signals.append('Sanierung = KfW-Förderung hochattraktiv')
        if 'anbau' in text_l or 'aufstockung' in text_l:
            signals.append('Erweiterung = Anschlussfinanzierung oder Sondertilgung möglich')
        if not signals:
            signals.append('Öffentlich genehmigte Baumaßnahme = aktiver Finanzierungsbedarf')
        signals.append('Frisch eingereicht – noch kein Berater kontaktiert')
        return signals

    def _extract_title(self, element) -> str:
        for tag in ['h1', 'h2', 'h3', 'h4', 'strong']:
            el = element.find(tag)
            if el:
                return el.get_text(strip=True)[:120]
        return ''

    def _extract_location(self, text: str) -> str:
        for city in REGION_CITIES:
            if city.lower() in text.lower():
                return city
        return 'Bremen Region'

    def _extract_link(self, element, base: str) -> str:
        link = element.find('a', href=True)
        if link:
            href = link['href']
            return href if href.startswith('http') else base + href
        return ''


if __name__ == '__main__':
    BaugenehmigungScraper().run()
