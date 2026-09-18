#!/usr/bin/env python3
"""Seed ofertas de prueba vía API admin.

Uso:
  $env:ADMIN_KEY="..."
  $env:API_BASE="https://TU-API.onrender.com"
  python scripts/seed_test_leads.py --agency hebron-real-estate --count 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agency", required=True, help="agency_id o slug")
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--keep-credits", action="store_true", help="no poner cupo en 0")
    p.add_argument("--api", default=os.environ.get("API_BASE", "http://localhost:8000"))
    p.add_argument("--admin-key", default=os.environ.get("ADMIN_KEY", ""))
    args = p.parse_args()
    if not args.admin_key:
        print("Falta ADMIN_KEY", file=sys.stderr)
        return 1
    body = {
        "agency_id": args.agency,
        "count": args.count,
        "zero_credits": not args.keep_credits,
    }
    req = urllib.request.Request(
        f"{args.api.rstrip('/')}/admin/seed-test-leads",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Admin-Key": args.admin_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
