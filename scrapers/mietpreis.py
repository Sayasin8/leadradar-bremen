"""
Mietpreis Scraper – Eigenständiges Skript
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.wettbewerber import MietpreisScraper

if __name__ == '__main__':
    MietpreisScraper().run()
