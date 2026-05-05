"""
LeadRadar Scheduler
Führt alle Scraper automatisch in festgelegten Intervallen aus.
Starte dieses Skript parallel zum Flask-Server: python scheduler.py
"""

import schedule
import time
import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Scheduler] %(message)s'
)
log = logging.getLogger('scheduler')

SCRAPER_SCHEDULE = {
    'scrapers/baugenehmigungen.py':  {'interval': 'daily',   'time': '08:00'},
    'scrapers/handelsregister.py':   {'interval': 'daily',   'time': '08:15'},
    'scrapers/kleinanzeigen.py':     {'interval': '4hours'},
    'scrapers/wg_gesucht.py':        {'interval': '6hours'},
    'scrapers/wettbewerber.py':      {'interval': 'daily',   'time': '09:00'},
    'scrapers/schwarzesbrett.py':    {'interval': '12hours'},
    'scrapers/mietpreis.py':         {'interval': 'weekly',  'weekday': 'monday', 'time': '07:00'},
}


def run_scraper(script: str):
    log.info(f"▶ Starte {script}")
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log.info(f"✅ {script} erfolgreich")
        else:
            log.error(f"❌ {script} Fehler:\n{result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        log.warning(f"⏱ {script} Timeout nach 120s")
    except Exception as e:
        log.error(f"💥 {script} Exception: {e}")


def setup_schedule():
    for script, cfg in SCRAPER_SCHEDULE.items():
        interval = cfg['interval']

        if interval == 'daily':
            t = cfg.get('time', '09:00')
            schedule.every().day.at(t).do(run_scraper, script)
            log.info(f"📅 {script} täglich um {t}")

        elif interval == '4hours':
            schedule.every(4).hours.do(run_scraper, script)
            log.info(f"📅 {script} alle 4 Stunden")

        elif interval == '6hours':
            schedule.every(6).hours.do(run_scraper, script)
            log.info(f"📅 {script} alle 6 Stunden")

        elif interval == '12hours':
            schedule.every(12).hours.do(run_scraper, script)
            log.info(f"📅 {script} alle 12 Stunden")

        elif interval == 'weekly':
            weekday = cfg.get('weekday', 'monday')
            t = cfg.get('time', '07:00')
            getattr(schedule.every(), weekday).at(t).do(run_scraper, script)
            log.info(f"📅 {script} jeden {weekday} um {t}")


def run_all_now():
    """Einmalig alle Scraper jetzt ausführen"""
    log.info("🚀 Führe alle Scraper einmalig aus...")
    for script in SCRAPER_SCHEDULE.keys():
        run_scraper(script)


if __name__ == '__main__':
    log.info("=" * 50)
    log.info("LeadRadar Scheduler gestartet")
    log.info("=" * 50)

    if '--now' in sys.argv:
        run_all_now()
    else:
        setup_schedule()
        log.info("⏳ Warte auf geplante Ausführungen...")
        while True:
            schedule.run_pending()
            time.sleep(60)
