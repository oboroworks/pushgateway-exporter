import yaml
from typing import List, Dict
from pydantic import BaseModel, ValidationError

class ConfigError(Exception):
    pass

class ServiceConfig(BaseModel):
    name: str
    freshness_threshold_seconds: int


def _parse_services(services: List[Dict]) -> List[ServiceConfig]:
    try:
        return [ServiceConfig(**service) for service in services]
    except ValidationError as e:
        raise ConfigError(f"Service configuration validation error: {e}")


class Config:
    def __init__(self, config_path: str):
        self._data = self._load_config(config_path)
        self._services: List[ServiceConfig] = _parse_services(self._data.get("services", []))

    @staticmethod
    def _load_config(path: str) -> Dict:
        try:
            with open(path, 'r') as file:
                config = yaml.safe_load(file)
        except Exception as e:
            raise ConfigError(f"Failed to load configuration file: {e}")

        if not isinstance(config, dict):
            raise ConfigError("Configuration file format error: expected a dictionary.")

        required_fields = ["pushgateway_url"]
        for field in required_fields:
            if field not in config:
                raise ConfigError(f"Missing required configuration field: {field}")

        return config

    def get_pushgateway_url(self) -> str:
        return self._data["pushgateway_url"].rstrip('/')

    def get_scraper_interval(self) -> int:
        return int(self._data.get("scrape_interval_seconds", 10))

    def get_default_freshness(self) -> int:
        return int(self._data.get("default_freshness_threshold_seconds", 10))

    def get_active_scrape_services(self) -> List[ServiceConfig]:
        return self._services