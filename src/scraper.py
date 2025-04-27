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
        for service in self.services:
            service_name = service.name
            freshness_threshold = service.freshness_threshold_seconds
            pattern = re.compile(
                rf'^loop_heartbeat_timestamp_seconds\{{[^}}]*instance="{re.escape(service_name)}"[^}}]*\}} ([0-9\.e\+\-]+)$'
            )
            found = False
            for line in lines:
                match = pattern.match(line)
                if match:
                    timestamp = int(float(match.group(1)))
                    age = now - timestamp
                    if age < freshness_threshold:
                        self.service_status[service_name] = 1
                    else:
                        self.service_status[service_name] = 0
                    found = True
                    break
            if not found:
                self.service_status[service_name] = 0

    async def get_service_status(self, service_name: str) -> int:
        if service_name not in {service.name for service in self.services}:
            raise FileNotFoundError(f"Service '{service_name}' not configured as active")

        now = time.time()
        if self._last_fetch and (now - self._last_fetch) < self.scrape_interval_seconds:
            return self.service_status.get(service_name, 0)

        metrics = await self.fetch_metrics()

        self.process_metrics(metrics)
        self._last_fetch = now

        return self.service_status.get(service_name, 0)
