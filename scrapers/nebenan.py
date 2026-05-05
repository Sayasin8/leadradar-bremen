"""
Nebenan.de Premium Lead Generator
Hyperlokal, echte Kaufsignale direkt aus der Nachbarschaft.

Erkennt automatisch:
- Beamte & öffentlicher Dienst
- Unternehmer & Selbstständige
- Familien mit Kindern
- Zuzügler in die Region
- Umzugssignale aller Art
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from scrapers.base import BaseScraper, REGION_CITIES

# Signalwörter pro Zielgruppe
BEAMTEN_SIGNALE = [
    'lehrer', 'lehrerin', 'beamte', 'beamtin', 'polizei', 'polizistin',
    'staatsanwalt', 'richter', 'finanzamt', 'bundeswehr', 'stadt bremen',
    'behörde', 'amt', 'öffentlicher dienst', 'verwaltung', 'stadtamt'
]

UNTERNEHMER_SIGNALE = [
    'selbstständig', 'gmbh', 'geschäftsführer', 'inhaber', 'gründer',
    'startup', 'freiberuflich', 'freelancer', 'unternehmer', 'eigene firma',
    'agentur', 'praxis', 'kanzlei', 'büro eröffnet', 'ich habe gegründet'
]

FAMILIEN_SIGNALE = [
    'kinder', 'kind', 'baby', 'schwanger', 'nachwuchs', 'familie',
    'kindergarten', 'schule', 'eltern', 'wir werden mehr',
    'zuwachs', 'zwillinge', 'kleinkind', 'dritter kommt'
]

ZUZUG_SIGNALE = [
    'neu hier', 'neu in bremen', 'gerade zugezogen', 'bin neu',
    'umgezogen', 'wir sind neu', 'hierher gezogen', 'frisch in',
    'aus hamburg', 'aus berlin', 'aus münchen', 'aus köln',
    'aus hannover', 'aus dem ausland', 'neu in der nachbarschaft'
]

KAUF_SIGNALE = [
    'kaufen', 'eigentum', 'eigenheim', 'haus kaufen', 'wohnung kaufen',
    'immobilie', 'neubau', 'bauen', 'makler', 'finanzierung',
    'kredit', 'wir suchen', 'auf der suche', 'träume', 'zuhause'
]

FRUSTRATIONS_SIGNALE = [
    'miete erhöht', 'kündigung', 'eigenbedarfskündigung', 'muss raus',
    'suche dringend', 'verzweifelt', 'mietpreise', 'zu teuer',
    'kann mir nicht leisten', 'miete wahnsinn', 'vermieter'
]

# Bremen-Region Stadtteile für Nebenan.de
STADTTEILE = [
    'findorff', 'schwachhausen', 'horn', 'borgfeld', 'oberneuland',
    'vegesack', 'blumenthal', 'burglesum', 'hemelingen', 'vahr',
    'osterholz', 'neustadt', 'walle', 'gröpelingen', 'östliche-vorstadt',
    'mitte', 'söhren', 'lesum'
]

UMLAND_STAEDTE = [
    'stuhr', 'weyhe', 'syke', 'achim', 'oyten', 'lilienthal',
    'worpswede', 'ganderkesee', 'delmenhorst', 'verden'
]


class NebenanScraper(BaseScraper):
    source = 'wg'  # Ersetzt WG-Gesucht im Dashboard
    source_label = 'Nebenan.de'

    def run(self):
        self.logger.info("Starte Nebenan.de Premium Lead Generator...")
        self._scrape_stadtteile()
        self._scrape_umland()
        self._scrape_via_search()
        self.print_summary()

    def _scrape_stadtteile(self):
        """Scannt Bremer Stadtteile auf Nebenan.de"""
        for stadtteil in STADTTEILE:
            url = f'https://nebenan.de/feed/{stadtteil}'
            soup = self.fetch(url)
            if not soup:
                continue
            self._process_page(soup, f'Bremen {stadtteil.title()}')

    def _scrape_umland(self):
        """Scannt Umlandgemeinden"""
        for stadt in UMLAND_STAEDTE:
            url = f'https://nebenan.de/feed/{stadt}'
            soup = self.fetch(url)
            if not soup:
                continue
            self._process_page(soup, stadt.title())

    def _scrape_via_search(self):
        """Sucht gezielt nach Kaufsignalen"""
        search_terms = [
            'haus kaufen', 'wohnung kaufen', 'umzug', 'neue nachbarschaft',
            'eigenheim', 'finanzierung', 'makler empfehlung'
        ]
        for term in search_terms:
            url = f'https://nebenan.de/search?q={term.replace(" ", "+")}&location=Bremen'
            soup = self.fetch(url)
            if not soup:
                continue
            self._process_page(soup, 'Bremen Region')

    def _process_page(self, soup, location: str):
        """Verarbeitet eine Nebenan.de Seite"""
        # Posts können in verschiedenen Container-Elementen sein
        posts = soup.find_all(['article', 'div', 'li'],
                               class_=re.compile(r'post|feed|item|card|entry', re.I))

        # Fallback: Alle Textblöcke
        if not posts:
            posts = soup.find_all('p', limit=30)

        for post in posts[:25]:
            text = post.get_text(separator=' ', strip=True)
            if len(text) < 40:
                continue

            text_l = text.lower()

            # Relevanzcheck – mindestens ein Signal muss vorhanden sein
            all_signals_raw = (BEAMTEN_SIGNALE + UNTERNEHMER_SIGNALE +
                               FAMILIEN_SIGNALE + ZUZUG_SIGNALE +
                               KAUF_SIGNALE + FRUSTRATIONS_SIGNALE)
            if not any(s in text_l for s in all_signals_raw):
                continue

            # Zielgruppen bestimmen
            zielgruppe = self._detect_zielgruppe(text_l)
            if not zielgruppe:
                continue

            # URL extrahieren
            link_el = post.find('a', href=True)
            url = ''
            if link_el:
                href = link_el['href']
                url = href if href.startswith('http') else 'https://nebenan.de' + href

            if self.lead_exists(url):
                continue

            # Titel extrahieren
            title_el = post.find(['h2', 'h3', 'h4', 'strong', 'a'])
            title = title_el.get_text(strip=True)[:100] if title_el else text[:80]

            signals = self._build_signals(text_l, zielgruppe)
            score = self._calc_score(text_l, zielgruppe, signals)
            outreach = self._build_outreach(zielgruppe, text_l)

            self.save_lead(
                title=f'Nebenan.de · {zielgruppe["label"]}: {title[:80]}',
                description=text[:350],
                location=location,
                score=score,
                signals=signals,
                outreach=outreach,
                url=url or f'https://nebenan.de/feed/{location.lower().replace(" ", "-")}'
            )

    def _detect_zielgruppe(self, text_l: str) -> dict:
        """Erkennt die Zielgruppe und gibt Priorität zurück"""

        # Priorität: Frustrations > Beamte > Unternehmer > Familie > Zuzug > Kauf
        if any(s in text_l for s in FRUSTRATIONS_SIGNALE):
            return {'type': 'frustration', 'label': 'Miet-Frustration', 'base_score': 82}

        if any(s in text_l for s in BEAMTEN_SIGNALE):
            return {'type': 'beamte', 'label': 'Beamter / Öff. Dienst', 'base_score': 78}

        if any(s in text_l for s in UNTERNEHMER_SIGNALE):
            return {'type': 'unternehmer', 'label': 'Unternehmer', 'base_score': 75}

        if any(s in text_l for s in FAMILIEN_SIGNALE):
            # Nur wenn auch Kaufsignal oder Zuzug
            if any(s in text_l for s in KAUF_SIGNALE + ZUZUG_SIGNALE):
                return {'type': 'familie', 'label': 'Familie', 'base_score': 70}

        if any(s in text_l for s in ZUZUG_SIGNALE):
            return {'type': 'zuzug', 'label': 'Zuzügler', 'base_score': 68}

        if sum(1 for s in KAUF_SIGNALE if s in text_l) >= 2:
            return {'type': 'kauf', 'label': 'Kaufsignal', 'base_score': 62}

        return None

    def _build_signals(self, text_l: str, zielgruppe: dict) -> list:
        signals = []
        t = zielgruppe['type']

        if t == 'frustration':
            signals.append('Miet-Frustration erkannt = emotionaler Kauftrigger vorhanden')
            if 'eigenbedarfskündigung' in text_l:
                signals.append('Eigenbedarfskündigung = akuter Handlungsdruck')
            if 'miete erhöht' in text_l:
                signals.append('Mieterhöhung = perfekter Moment für Kauf-Argument')

        elif t == 'beamte':
            signals.append('Beamter/öff. Dienst = bestes Kreditprofil (unkündbar, sicher)')
            signals.append('Banken vergeben an Beamte oft Sonderkonditionen')

        elif t == 'unternehmer':
            signals.append('Unternehmer = hohes Finanzierungsvolumen möglich')
            signals.append('Selbstständige brauchen spezialisierten Berater (Einkommensnachweise)')

        elif t == 'familie':
            signals.append('Familie = KfW-Kinderzuschuss bis 30.000€ möglich')
            signals.append('Platzbedarf wächst = konkreter Kaufanlass')

        elif t == 'zuzug':
            signals.append('Zuzügler = oft offen für Eigenheim statt langfristige Miete')
            signals.append('Noch kein lokaler Berater bekannt = idealer Erstkontakt')

        elif t == 'kauf':
            signals.append('Mehrere Kaufsignale im Text erkannt')

        # Bonus-Signale
        if any(s in text_l for s in KAUF_SIGNALE):
            kauf_treffer = [s for s in KAUF_SIGNALE if s in text_l]
            signals.append(f'Direktes Kaufinteresse: "{", ".join(kauf_treffer[:3])}"')

        signals.append('Hyperlokal: Nachbarschafts-Post = echte Person, kein Bot')
        return signals

    def _calc_score(self, text_l: str, zielgruppe: dict, signals: list) -> int:
        score = zielgruppe['base_score']

        # Bonus für Kaufsignale
        kauf_count = sum(1 for s in KAUF_SIGNALE if s in text_l)
        score += min(10, kauf_count * 3)

        # Bonus für Dringlichkeit
        if any(w in text_l for w in ['dringend', 'sofort', 'schnell', 'asap']):
            score += 8

        # Bonus für Eigenkapital-Hinweise
        if any(w in text_l for w in ['eigenkapital', 'gespart', 'erspartes']):
            score += 7

        return min(97, score)

    def _build_outreach(self, zielgruppe: dict, text_l: str) -> str:
        t = zielgruppe['type']

        if t == 'frustration':
            if 'eigenbedarfskündigung' in text_l:
                return (
                    'Eine Eigenbedarfskündigung ist stressig – aber oft der Moment, '
                    'in dem Kaufen plötzlich sinnvoller ist als erneut zu mieten. '
                    'Ich zeige Ihnen in 30 Minuten ob und was für Sie finanzierbar ist.'
                )
            return (
                'Steigende Mieten machen Kaufen in vielen Bremer Stadtteilen günstiger '
                'als weiter zu mieten. Ich rechne das kostenlos für Ihre Situation durch – '
                'ohne Verpflichtung.'
            )

        elif t == 'beamte':
            return (
                'Als Beamter oder Beschäftigter im öffentlichen Dienst gehören Sie zu den '
                'attraktivsten Kreditnehmern überhaupt. Viele Banken bieten Ihnen Sonderkonditionen '
                'die andere nicht bekommen – ich hole das Beste für Sie raus.'
            )

        elif t == 'unternehmer':
            return (
                'Selbstständige haben bei der Baufinanzierung besondere Anforderungen – '
                'Einkommensnachweise, Bilanzen, Struktur. Ich bin spezialisiert auf genau diese '
                'Situation und finde die Bank die Ihr Profil wirklich versteht.'
            )

        elif t == 'familie':
            return (
                'Für Familien mit Kindern gibt es aktuell KfW-Förderungen die viele Berater '
                'übersehen – bis zu 30.000€ zusätzlich. Ich prüfe kostenlos welche Programme '
                'für Ihre Familie infrage kommen.'
            )

        elif t == 'zuzug':
            return (
                'Willkommen in der Region! Viele Zuzügler entscheiden sich innerhalb des ersten '
                'Jahres für Eigentum statt Miete – gerade wenn man plant zu bleiben. '
                'Ich helfe Ihnen beim Einstieg in die Bremer Immobilienfinanzierung.'
            )

        return (
            'Ich habe Ihren Post gesehen und würde mich freuen, Ihnen als spezialisierter '
            'Baufinanzierungsberater in der Region Bremen zu helfen. Kostenlos und unverbindlich.'
        )


if __name__ == '__main__':
    NebenanScraper().run()
