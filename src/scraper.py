import aiohttp
import time
import re
from typing import Dict, Optional

from src.config import Config, ServiceConfig

class HeartbeatScraper:
    def __init__(self, config: Config):
        self.pushgateway_url = config.get_pushgateway_url()
        self.scrape_interval_seconds = config.get_scraper_interval()
        self.services: list[ServiceConfig] = config.get_active_scrape_services()
        self.default_threshold = config.get_default_freshness()
        self.services_thresholds = {s.name: s.freshness_threshold_seconds for s in self.services}
        self.session: Optional[aiohttp.ClientSession] = None
        self.service_status: Dict[str, int] = {service.name: 0 for service in self.services}
        self._last_fetch: Optional[float] = None

    async def start_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10))

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def fetch_metrics(self) -> str:
        await self.start_session()
        async with self.session.get(f"{self.pushgateway_url}/metrics") as response:
            response.raise_for_status()
            resp = await response.text()
            return resp

    def process_metrics(self, metrics: str):
        now = time.time()
        lines = metrics.splitlines()
        for line in lines:
            if line.startswith("loop_heartbeat_timestamp_seconds"):
                string_match = re.match(
                    r'loop_heartbeat_timestamp_seconds\{[^}]*instance="([^"]+)"[^}]*\} ([0-9\.e\+\-]+)',
                    line
                )
                if string_match:
                    instance = string_match.group(1)
                    timestamp = float(string_match.group(2))
                    age = now - timestamp
                    freshness_threshold = self.services_thresholds.get(instance, self.default_threshold)

                    if age < freshness_threshold:
                        self.service_status[instance] = 1  # Service is fresh
                    else:
                        self.service_status[instance] = 0  # Service is expired
        self._last_fetch = now

    async def get_service_status(self, service_name: str) -> int:
        now = time.time()
        if self._last_fetch and (now - self._last_fetch) < self.scrape_interval_seconds:
            return self.service_status.get(service_name, 0)

        metrics = await self.fetch_metrics()
        self.process_metrics(metrics)

        return self.service_status.get(service_name, 0)

    async def get_services(self):
        now = time.time()
        if not self._last_fetch or (now - self._last_fetch > self.scrape_interval_seconds):
            metrics = await self.fetch_metrics()
            self.process_metrics(metrics)
        return self.service_status