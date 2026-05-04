"""Simuleaza un senzor IoT - trimite citiri periodic la API."""

from __future__ import annotations

import argparse
import random
import sys
import time

import httpx

from app.config import settings


def login(api: str, username: str, password: str) -> str:
    r = httpx.post(
        f"{api}/auth/login",
        data={"username": username, "password": password},
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def send_one(api: str, token: str, rng: random.Random) -> dict:
    body = {
        "lat": 46.77 + rng.uniform(-0.05, 0.05),
        "lon": 23.62 + rng.uniform(-0.05, 0.05),
        "ph": round(rng.uniform(5.0, 8.0), 2),
        "umiditate": round(rng.uniform(15, 90), 1),
        "temperatura": round(rng.uniform(0, 38), 1),
    }
    r = httpx.post(
        f"{api}/sensors/analiza",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default=settings.dashboard_api_url)
    p.add_argument("--username", default="fermier")
    p.add_argument("--password", default="agrosmart2025")
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    rng = random.Random(args.seed)
    try:
        token = login(args.api, args.username, args.password)
    except httpx.HTTPError as exc:
        print(f"Login esuat: {exc}", file=sys.stderr)
        return 1

    print(f"Conectat la {args.api}. Trimit {args.count} citiri (interval {args.interval}s)")
    for i in range(1, args.count + 1):
        try:
            res = send_one(args.api, token, rng)
        except httpx.HTTPError as exc:
            print(f"  [{i}] EROARE: {exc}")
            continue
        flag = "ALERTA " if res["alerta"] else ""
        print(f"  [{i}] {flag}{res['actiune']:<22} | {res['motiv']}")
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
