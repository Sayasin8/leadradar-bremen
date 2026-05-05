"""
Basis-Klasse für alle LeadRadar Scraper
"""

import sqlite3
import json
import time
import random
import logging
from datetime import datetime
from typing import Optional
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

DB_PATH = 'data/leads.db'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
}

# Bremen + 50km PLZ-Bereich (Auswahl repräsentativ)
REGION_PLZ = [
    '28195', '28199', '28203', '28205', '28207', '28209', '28211', '28213',
    '28215', '28217', '28219', '28237', '28239', '28259', '28277', '28279',
    '28307', '28309', '28325', '28327', '28329', '28355', '28357', '28359',
    '28717', '28719', '28755', '28757', '28759', '28777', '28779',
    '27749', '27751', '27753', '27755', '27777',
    '28816', '28832', '28844', '28857', '28876', '28879',
    '27283', '27305', '27321', '27356', '27374',
    '26122', '26127', '26131', '26133', '26135',
    '27570', '27574', '27576', '27578',
]

REGION_CITIES = [
    'Bremen', 'Delmenhorst', 'Oldenburg', 'Bremerhaven',
    'Stuhr', 'Achim', 'Verden', 'Oyten', 'Syke',
    'Ganderkesee', 'Weyhe', 'Lilienthal', 'Worpswede'
]


class BaseScraper:
    """Basisklasse für alle Scraper"""

    source = ''
    source_label = ''
    logger = None

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.new_leads = 0
        self.skipped = 0

    def get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def lead_exists(self, url: str) -> bool:
        """Prüft ob Lead (via URL) schon existiert"""
        if not url:
            return False
        conn = self.get_db()
        exists = conn.execute(
            'SELECT 1 FROM leads WHERE url = ? LIMIT 1', [url]
        ).fetchone()
        conn.close()
        return bool(exists)

    def save_lead(
        self,
        title: str,
        description: str,
        location: str,
        score: int,
        signals: list,
        outreach: str = '',
        url: str = '',
        plz: str = '',
        raw_data: dict = None
    ):
        """Speichert einen Lead in der Datenbank"""
        if self.lead_exists(url):
            self.skipped += 1
            return False

        conn = self.get_db()
        conn.execute('''
            INSERT INTO leads
                (source, source_label, title, description, location, plz,
                 score, signals, outreach, url, raw_data, is_hot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            self.source,
            self.source_label,
            title,
            description,
            location,
            plz,
            score,
            json.dumps(signals, ensure_ascii=False),
            outreach,
            url,
            json.dumps(raw_data or {}, ensure_ascii=False),
            1 if score >= 80 else 0
        ])
        conn.commit()
        conn.close()
        self.new_leads += 1
        self.logger.info(f"✅ Lead gespeichert (Score {score}): {title[:60]}")
        return True

    def fetch(self, url: str, params=None, timeout=15) -> Optional[BeautifulSoup]:
        """HTTP GET mit Error-Handling und Delay"""
        try:
            time.sleep(random.uniform(1.5, 3.5))
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        except requests.RequestException as e:
            self.logger.error(f"Fehler beim Abrufen von {url}: {e}")
            return None

    def score_lead(self, signals: list, base: int = 50) -> int:
        """Einfaches regelbasiertes Scoring"""
        score = base
        for signal in signals:
            signal_lower = signal.lower()
            if any(w in signal_lower for w in ['unbefristet', 'festangestellt', 'beamte', 'arzt', 'ärztin']):
                score += 8
            if any(w in signal_lower for w in ['eigenkapital', 'sofort', 'konkret']):
                score += 7
            if any(w in signal_lower for w in ['familie', 'kinder', 'kfw']):
                score += 5
            if any(w in signal_lower for w in ['unternehmer', 'gmbh', 'selbstständig']):
                score += 6
            if any(w in signal_lower for w in ['abgelehnt', 'enttäuscht', 'schlechte erfahrung']):
                score += 10
        return min(99, max(10, score))

    def run(self):
        """Override in jeder Unterklasse"""
        raise NotImplementedError

    def print_summary(self):
        self.logger.info(
            f"🏁 Fertig: {self.new_leads} neue Leads gespeichert, "
            f"{self.skipped} bereits bekannt übersprungen."
        )
