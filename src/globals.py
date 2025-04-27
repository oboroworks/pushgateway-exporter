import os

from src.config import Config
from src.scraper import HeartbeatScraper

CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config.yml')
config = Config(CONFIG_PATH)
scraper = HeartbeatScraper(config)
