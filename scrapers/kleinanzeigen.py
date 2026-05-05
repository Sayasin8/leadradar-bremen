"""
Kleinanzeigen.de Scraper
Ziel: Kaufgesuche, Verkaufsanzeigen, Umzugssignale in der Region Bremen
Hinweis: Nur öffentliche Suchergebnisse, kein automatisches Massenanschreiben.
         Dieses Tool dient der Signalidentifikation.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import time
from scrapers.base import BaseScraper, REGION_CITIES

SEARCH_TERMS = [
    'Haus kaufen gesucht',
    'Wohnung kaufen gesucht',
    'Grundstück kaufen',
    'Baugrundstück gesucht',
    'Eigenheim gesucht',
    'Eigentumswohnung gesucht',
    'Neubau suche Finanzierung',
]

REGION_QUERY = 'Bremen'


class KleinanzeigenScraper(BaseScraper):
    source = 'kleinanzeige'
    source_label = 'Kleinanzeigen'

    BASE_URL = 'https://www.kleinanzeigen.de/s-{region}/{query}/k0'
    LIST_URL = 'https://www.kleinanzeigen.de/s-immobilien/bremen/c195l328+r50'

    def run(self):
        self.logger.info("Starte Kleinanzeigen-Scraper...")
        self._scrape_kaufgesuche()
        self._scrape_verkaufsanzeigen()
        self.print_summary()

    def _scrape_kaufgesuche(self):
        """Kaufgesuche: Menschen die aktiv ein Haus/Wohnung suchen"""
        url = 'https://www.kleinanzeigen.de/s-immobilien/bremen/kaufgesuch/c195l328+r50'
        soup = self.fetch(url)
        if not soup:
            return

        ads = soup.find_all('article', class_=re.compile(r'aditem|ad-item|result'))
        if not ads:
            ads = soup.find_all(['li', 'div'], {'data-adid': True})

        for ad in ads[:20]:
            self._process_ad(ad, is_kaufgesuch=True)

    def _scrape_verkaufsanzeigen(self):
        """Private Verkaufsanzeigen: Käufer noch nicht finanziert"""
        url = self.LIST_URL
        soup = self.fetch(url)
        if not soup:
            return

        ads = soup.find_all('article', class_=re.compile(r'aditem|ad-item'))
        if not ads:
            ads = soup.find_all(['li', 'div'], {'data-adid': True})

        for ad in ads[:25]:
            self._process_ad(ad, is_kaufgesuch=False)

    def _process_ad(self, ad_element, is_kaufgesuch: bool):
        title_el = ad_element.find(['h2', 'h3', 'a'], class_=re.compile(r'title|headline'))
        if not title_el:
            title_el = ad_element.find('a')
        if not title_el:
            return

        title = title_el.get_text(strip=True)
        if not title or len(title) < 10:
            return

        link_el = ad_element.find('a', href=True)
        url = ''
        if link_el:
            href = link_el['href']
            url = href if href.startswith('http') else 'https://www.kleinanzeigen.de' + href

        if self.lead_exists(url):
            return

        desc_el = ad_element.find(['p', 'div'], class_=re.compile(r'desc|text|body'))
        description = desc_el.get_text(strip=True) if desc_el else ''

        price_el = ad_element.find(class_=re.compile(r'price|preis'))
        price_text = price_el.get_text(strip=True) if price_el else ''

        location_el = ad_element.find(class_=re.compile(r'location|ort|city'))
        location = location_el.get_text(strip=True) if location_el else 'Bremen Region'

        full_text = f'{title} {description} {price_text}'.lower()

        # Relevanzfilter
        relevant_keywords = [
            'haus', 'wohnung', 'etw', 'eigentum', 'grundstück', 'neubau',
            'kaufen', 'suche', 'gesucht', 'finanzierung'
        ]
        if not any(kw in full_text for kw in relevant_keywords):
            return

        signals = self._build_signals(title, description, price_text, is_kaufgesuch)
        score = self.score_lead(signals, base=52)
        outreach = self._build_outreach(title, is_kaufgesuch, price_text)

        self.save_lead(
            title=title[:120],
            description=f'{description[:250]} | Preis: {price_text}',
            location=location,
            score=score,
            signals=signals,
            outreach=outreach,
            url=url
        )

    def _build_signals(self, title: str, desc: str, price: str, is_kaufgesuch: bool) -> list:
        signals = []
        text = f'{title} {desc}'.lower()

        if is_kaufgesuch:
            signals.append('Aktives Kaufgesuch = Person sucht konkret und hat Kaufabsicht')
        else:
            signals.append('Privater Verkauf = Käufer noch nicht finanziert, Chance zur Ansprache')

        if 'eigenkapital' in text or 'eq' in text:
            signals.append('Eigenkapital erwähnt = ernsthafter Kaufinteressent')
        if 'festangestellt' in text or 'unbefristet' in text:
            signals.append('Festanstellung erwähnt = sichere Bonität')
        if any(w in text for w in ['familie', 'kinder', 'kind']):
            signals.append('Familie mit Kindern = KfW-Kinderbonus möglich (bis 30.000€)')
        if 'budget' in text or '€' in price:
            signals.append(f'Klares Budget definiert ({price.strip()}) = realistische Kaufabsicht')
        if 'ohne makler' in text or 'privat' in text:
            signals.append('Privatverkauf = direkter Zugang zum Käuferkreis')

        return signals

    def _build_outreach(self, title: str, is_kaufgesuch: bool, price: str) -> str:
        if is_kaufgesuch:
            return (
                f'Ihre Suchanzeige zeigt, dass Sie konkret auf Kaufsuche sind. '
                f'Als unabhängiger Baufinanzierungsberater prüfe ich für Sie kostenlos, '
                f'was im Rahmen von {price or "Ihrem Budget"} finanzierbar ist – '
                f'und welche Förderungen Sie zusätzlich nutzen können.'
            )
        return (
            f'Als Käufer dieser Immobilie brauchen Sie eine schnelle, solide Finanzierung. '
            f'Ich kann innerhalb von 48 Stunden eine belastbare Konditionsanfrage bei '
            f'50+ Banken stellen – ideal für private Verkäufe wo es auf Tempo ankommt.'
        )


if __name__ == '__main__':
    KleinanzeigenScraper().run()
