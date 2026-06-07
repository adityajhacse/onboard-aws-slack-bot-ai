#!/usr/bin/env python3
"""Print HCP Terraform VCS OAuth identifiers for an organization.

Usage:
  export HCP_TERRAFORM_TOKEN="..."
  python3 src/get_hcp_vcs_oauth_token_id.py --org your-org

Optional:
  export HCP_TERRAFORM_URL="https://app.terraform.io"
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
from urllib import error, request

import certifi


def _ssl_context():
    return ssl.create_default_context(cafile=certifi.where())


def _get_json(url: str, token: str) -> dict:
    req = request.Request(
        url=url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.api+json",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=30, context=_ssl_context()) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HCP API returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error calling HCP API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("HCP API returned a non-JSON response.") from exc


def _print_results(payload: dict) -> None:
    data = payload.get("data") or []
    if not data:
        print("No oauth clients found for this org.")
        return

    print("Found OAuth clients:\n")
    for item in data:
        client_id = item.get("id", "")
        attrs = item.get("attributes") or {}
        service_provider = attrs.get("service-provider", "")
        http_url = attrs.get("http-url", "")
        api_url = attrs.get("api-url", "")
        print(f"- client_id: {client_id}")
        print(f"  service_provider: {service_provider}")
        if http_url:
            print(f"  http_url: {http_url}")
        if api_url:
            print(f"  api_url: {api_url}")

        token_items = (
            ((item.get("relationships") or {}).get("oauth-tokens") or {}).get("data") or []
        )
        if token_items:
            token_ids = [entry.get("id", "") for entry in token_items if entry.get("id")]
            print(f"  oauth_token_ids: {', '.join(token_ids)}")
            print("  export command examples:")
            for token_id in token_ids:
                print(f'    export HCP_TERRAFORM_VCS_OAUTH_TOKEN_ID="{token_id}"')
        else:
            print("  oauth_token_ids: (none listed)")
        print("")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List HCP Terraform OAuth client/token IDs for VCS connections.",
    )
    parser.add_argument("--org", required=True, help="HCP Terraform organization name.")
    args = parser.parse_args()

    token = (
        os.environ.get("HCP_TERRAFORM_TOKEN", "").strip()
        or os.environ.get("TFC_TOKEN", "").strip()
    )
    if not token:
        raise SystemExit(
            "Set HCP_TERRAFORM_TOKEN (or TFC_TOKEN) before running this script."
        )

    base_url = os.environ.get("HCP_TERRAFORM_URL", "https://app.terraform.io").strip()
    url = f"{base_url}/api/v2/organizations/{args.org}/oauth-clients"
    payload = _get_json(url=url, token=token)
    _print_results(payload)


if __name__ == "__main__":
    main()
