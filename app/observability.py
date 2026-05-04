"""Logging structurat (JSON) + metrici Prometheus."""

from __future__ import annotations

import logging
import logging.config

from prometheus_client import CollectorRegistry, Counter

REGISTRY = CollectorRegistry()

nr_citiri_total = Counter(
    "agrosmart_citiri_total",
    "Numar total de citiri de senzor procesate",
    registry=REGISTRY,
)
nr_alerte_total = Counter(
    "agrosmart_alerte_total",
    "Numar total de alerte (decizii cu alerta=true)",
    registry=REGISTRY,
)
nr_login_fail = Counter(
    "agrosmart_login_fail_total",
    "Numar total de incercari esuate de login",
    registry=REGISTRY,
)
nr_ml_predict = Counter(
    "agrosmart_ml_predict_total",
    "Numar total de predictii ML",
    registry=REGISTRY,
)


def configure_logging(level: str = "INFO") -> None:
    """Configureaza logging JSON pe stdout."""
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": level, "handlers": ["console"], "propagate": False},
        },
    }
    logging.config.dictConfig(config)
