"""Lanseaza simultan FastAPI (Uvicorn) si dashboard-ul Gradio."""

from __future__ import annotations

import multiprocessing as mp
import os
import signal
import sys
import time

import uvicorn

from app.config import settings


def run_api() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info",
    )


def run_dashboard() -> None:
    # Import lazily so workers don't both import gradio
    from dashboard.app import main as dashboard_main

    # Asteapta putin sa porneasca API-ul
    time.sleep(2.0)
    dashboard_main()


def main() -> None:
    print(f"Pornesc {settings.app_name}")
    print(f"  API:        http://localhost:{settings.api_port}")
    print(f"  Docs:       http://localhost:{settings.api_port}/docs")
    print(f"  Dashboard:  http://localhost:{settings.dashboard_port}")
    print("Press Ctrl+C to stop.\n")

    api_p = mp.Process(target=run_api, name="agrosmart-api")
    dash_p = mp.Process(target=run_dashboard, name="agrosmart-dashboard")

    api_p.start()
    dash_p.start()

    def shutdown(*_: object) -> None:
        print("\nOpresc serviciile...")
        for p in (api_p, dash_p):
            if p.is_alive():
                os.kill(p.pid, signal.SIGTERM)  # type: ignore[arg-type]
        for p in (api_p, dash_p):
            p.join(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    api_p.join()
    dash_p.join()


if __name__ == "__main__":
    main()
