"""
Schwarzes Brett Scraper – Eigenständiges Skript
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.wettbewerber import SchwarzesBrettScraper

if __name__ == '__main__':
    SchwarzesBrettScraper().run()
