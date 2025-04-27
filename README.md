# Pushgateway Exporter

An **exporter** that allows you to monitor **heartbeat** and **status metrics** by scraping data from the **Pushgateway**. 
This project mimics the behavior of the **Blackbox Exporter**, but with the ability to perform custom probes for each monitored service, 
including managing **freshness** (expiry threshold for services).

### How it Works

The service exposes a `/probe` endpoint for each service target. The monitoring behavior is similar to **Blackbox Exporter**, allowing
to have consistent configuration for monitoring both HTTP `/ping` endpoints and recurrent loops.

### Configuration

The exporter scrapes metrics from the Pushgateway at the defined address and exposes them to Prometheus regularly.

### `docker-compose.yml` Configuration

You can start the exporter using `docker-compose`. The container configuration is as follows:

```yaml
version: '3.8'

services:
  pushgateway-exporter:
    image: pushgateway_exporter:latest
    container_name: pushgateway-exporter
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./config.yml:/app/config.yml
    networks:
      - network1

networks:
  network1:
    external: true
```

Example of `config.yml` for pushgateway-exporter

```yaml
pushgateway_url: "http://pushgateway:9091"
scrape_interval_seconds: 3

services:
  - name: service1
    freshness_threshold_seconds: 5
  - name: service2
    freshness_threshold_seconds: 5
```

Example of `prometheus.yml` job:

```yaml

  - job_name: 'ping-microservices-loops'
    metrics_path: /probe
    scrape_interval: 5s
    static_configs:
      - targets:
          - service1
      - targets:
          - service2
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: pushgateway-exporter:9116

```

To compare, this is a job for `prometheus.yml` with `blackbox-exporter`:

```yaml
  - job_name: 'ping-microservices-api'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - http://service1:8080
        labels:
          service: service1
      - targets:
          - http://service2:8080
        labels:
          service: service2
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

Example of pushgateway compliant client with asyncio:

```python
import aiohttp
import time
import logging
from typing import Optional

def bake_push_heartbeat(pushgateway_url: str, service_name: str, logger: Optional[logging.Logger] = None):
    pushgateway_url = f"{pushgateway_url.rstrip('/')}/metrics/job/heartbeat/instance/{service_name}"

    async def push_heartbeat():
        """Push an async heartbeat to a Prometheus Pushgateway."""
        now = int(time.time())
        payload = f'loop_heartbeat_timestamp_seconds{{service="{service_name}"}} {now}\n'

        headers = {
            'Content-Type': 'text/plain',
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(pushgateway_url, data=payload, headers=headers) as resp:
                    content = await resp.text(encoding='utf-8')
                    if resp.status not in (200, 202):
                        if logger:
                            logger.warning(f"Failed to push heartbeat: status={resp.status}, response='{content.strip()}'")
        except Exception as e:
            if logger:
                logger.warning(f"Exception while pushing heartbeat: {e}")

    return push_heartbeat

```

curl test call:

```bash
curl -X POST -H "Content-Type: text/plain" \
  --data "loop_heartbeat_timestamp_seconds{service=\"service1\"} $(date +%s)" \
  http://pushgateway-url:9116/metrics/job/heartbeat/instance/service1

```


