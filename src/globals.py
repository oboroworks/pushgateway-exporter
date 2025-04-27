# Copyright (c) 2025, Oboro Works LLC
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause License found in the
# LICENSE file in the root directory of this source tree.

import os

from src.config import Config
from src.scraper import HeartbeatScraper

CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config.yml')
config = Config(CONFIG_PATH)
scraper = HeartbeatScraper(config)
