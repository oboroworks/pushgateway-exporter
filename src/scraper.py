# Copyright (c) 2025, Oboro Works LLC
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause License found in the
# LICENSE file in the root directory of this source tree.

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
        self.replica_counts = {s.name: s.replica for s in self.services if s.replica is not None}
        self.session: Optional[aiohttp.ClientSession] = None
        self.service_status: Dict[str, int] = {service.name: 0 for service in self.services}
        self.service_replicas: Dict[str, set[str]] = {
            service.name: set() for service in self.services if service.replica is not None
        }
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

        for service in self.service_replicas:
            self.service_replicas[service].clear()

        pattern = re.compile(
            r'loop_heartbeat_timestamp_seconds\{[^}]*instance="([^"]+)",[^}]*service="([^"]+)"[^}]*\} ([0-9\.e\+\-]+)'
        )

        for match in pattern.finditer(metrics):
            instance = match.group(1)
            push_service_name = match.group(2)
            timestamp = float(match.group(3))
            age = now - timestamp

            freshness_threshold = (
                self.services_thresholds[push_service_name]
                if self.services_thresholds.get(push_service_name) is not None
                else self.default_threshold
            )

            # No replica has been declared in the config.yml file, and the push has not instance data
            if not push_service_name in self.replica_counts and instance == push_service_name:
                self.service_status[push_service_name] = 1 if age < freshness_threshold else 0

            # No replica has been declared in the config file, but the push has instance data

            elif not push_service_name in self.replica_counts:
                if age < freshness_threshold:
                    self.service_status[push_service_name] = 1
                    self.service_replicas.setdefault(push_service_name, set()).add(instance)
                else:
                    self.service_status[push_service_name] = 0
                    try:
                        self.service_replicas.setdefault(push_service_name, set()).remove(instance)
                        if not self.service_replicas[push_service_name]:
                            self.service_replicas.pop(push_service_name)
                    except KeyError:
                        ...

            # Else case, replica count has been defined
            else:
                if age < freshness_threshold:
                    self.service_replicas[push_service_name].add(instance)
                else:
                    try:
                        self.service_replicas[push_service_name].remove(instance)
                    except KeyError:
                        ...


        for service_name, expected_replicas in self.replica_counts.items():
            fresh_replicas = len(self.service_replicas[service_name])
            self.service_status[service_name] = 1 if fresh_replicas >= expected_replicas else 0

        self._last_fetch = now

    async def get_service_status(self, service_name: str) -> int:
        now = time.time()
        if self._last_fetch and (now - self._last_fetch) < self.scrape_interval_seconds:
            return self.service_status.get(service_name, 0)

        metrics = await self.fetch_metrics()
        self.process_metrics(metrics)

        return self.service_status.get(service_name, 0)

    async def get_configuration(self):
        now = time.time()
        if not self._last_fetch or (now - self._last_fetch > self.scrape_interval_seconds):
            metrics = await self.fetch_metrics()
            self.process_metrics(metrics)
        return {
            'status': self.service_status,
            'replicas': self.replica_counts,
            'service_replicas': self.service_replicas
        }
