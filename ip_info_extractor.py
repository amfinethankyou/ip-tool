#!/usr/bin/env python3
"""
IP Info Extractor – Powerful IP intelligence at your fingertips.

Supports single and batch lookups, multiple output formats (table / JSON / CSV),
automatic own-IP detection, reverse-DNS, and proxy/VPN/hosting/mobile flags.
"""

import csv
import json
import socket
import sys
import argparse
import ipaddress
from io import StringIO

import requests
from rich import box
from rich.console import Console
from rich.table import Table

# ── API configuration ────────────────────────────────────────────────────────

BATCH_API_URL  = "http://ip-api.com/batch"
SINGLE_API_URL = "http://ip-api.com/json/{ip}"
OWN_IP_API_URL = "http://ip-api.com/json/"
REQUEST_TIMEOUT = 10

# Fields requested from the API (includes paid flags available in the free tier)
API_FIELDS = (
    "query,status,message,country,countryCode,regionName,city,"
    "zip,lat,lon,isp,org,as,timezone,mobile,proxy,hosting"
)

# Display order and labels for output
FIELD_ORDER = [
    "query", "country", "countryCode", "regionName", "city",
    "zip", "lat", "lon", "isp", "org", "as",
    "timezone", "mobile", "proxy", "hosting", "rdns",
]

FIELD_LABELS = {
    "query":       "IP Address",
    "country":     "Country",
    "countryCode": "Country Code",
    "regionName":  "Region",
    "city":        "City",
    "zip":         "ZIP",
    "lat":         "Latitude",
    "lon":         "Longitude",
    "isp":         "ISP",
    "org":         "Organization",
    "as":          "AS Number",
    "timezone":    "Timezone",
    "mobile":      "Mobile Network",
    "proxy":       "Proxy / VPN",
    "hosting":     "Hosting / DC",
    "rdns":        "Reverse DNS",
}

# ── Console ──────────────────────────────────────────────────────────────────

# Honour --no-color at module init so all helper functions share one instance.
console = Console(no_color="--no-color" in sys.argv)

# ── Helpers ──────────────────────────────────────────────────────────────────


def validate_ip(ip: str) -> bool:
    """Return True if *ip* is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def reverse_dns(ip: str) -> str:
    """Return the PTR record for *ip*, or 'N/A' if none exists."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror):
        return "N/A"


def enrich(data: dict) -> dict:
    """Normalise boolean flags and add reverse-DNS to a result dict."""
    data["mobile"]  = "Yes" if data.get("mobile")  else "No"
    data["proxy"]   = "Yes" if data.get("proxy")   else "No"
    data["hosting"] = "Yes" if data.get("hosting") else "No"
    data["rdns"]    = reverse_dns(data["query"])
    return data


# ── Network layer ────────────────────────────────────────────────────────────


def _abort(exc: Exception) -> None:
    """Print a network error message and exit."""
    if isinstance(exc, requests.exceptions.Timeout):
        console.print("[bold red]Error:[/] Request timed out.")
    else:
        console.print(f"[bold red]Error:[/] Network error – {exc}")
    sys.exit(1)


def fetch_single(ip: str) -> dict:
    """Fetch geo-data for a single IP address."""
    try:
        url = SINGLE_API_URL.format(ip=ip) + f"?fields={API_FIELDS}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        _abort(exc)
        return {}  # unreachable; satisfies type-checkers


def fetch_own_ip() -> dict:
    """Fetch geo-data for the machine's own public IP."""
    try:
        resp = requests.get(OWN_IP_API_URL + f"?fields={API_FIELDS}", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        _abort(exc)
        return {}  # unreachable; satisfies type-checkers


def fetch_batch(ips: list) -> list:
    """Fetch geo-data for up to 100 IPs in one HTTP call."""
    try:
        payload = [{"query": ip, "fields": API_FIELDS} for ip in ips]
        resp = requests.post(BATCH_API_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        _abort(exc)
        return []  # unreachable; satisfies type-checkers


def lookup_ips(ips: list) -> list:
    """Validate, fetch and enrich data for a list of IP strings."""
    valid, invalid = [], []
    for ip in ips:
        (valid if validate_ip(ip) else invalid).append(ip)

    for ip in invalid:
        console.print(f"[bold red]Invalid IP:[/] '{ip}' – skipped.")

    if not valid:
        return []

    raw: list = []
    # Batch in chunks of 100 (API limit); use single endpoint for lone IPs
    for i in range(0, len(valid), 100):
        chunk = valid[i : i + 100]
        if len(chunk) == 1:
            raw.append(fetch_single(chunk[0]))
        else:
            raw.extend(fetch_batch(chunk))

    results = []
    for data in raw:
        if data.get("status") == "fail":
            console.print(
                f"[bold red]Lookup failed for {data.get('query', '?')}:[/] "
                f"{data.get('message')}"
            )
            continue
        results.append(enrich(data))

    return results


# ── Output renderers ─────────────────────────────────────────────────────────


def render_table(results: list) -> None:
    """Pretty-print each result as a Rich table."""
    for data in results:
        table = Table(
            title=(
                f"[bold cyan]IP Intelligence Report[/]  [dim]•[/]  "
                f"[bold yellow]{data['query']}[/]"
            ),
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            border_style="cyan",
            min_width=54,
        )
        table.add_column("Field", style="bold green", min_width=18)
        table.add_column("Value", style="white",      min_width=28)

        for key in FIELD_ORDER:
            label = FIELD_LABELS.get(key, key)
            value = str(data.get(key, "N/A"))
            # Highlight security-relevant flags
            if key in ("proxy", "mobile", "hosting") and value == "Yes":
                value = f"[bold yellow]{value}[/]"
            table.add_row(label, value)

        console.print(table)
        console.print()


def render_json(results: list) -> str:
    """Return a JSON string (single object for one result, array otherwise)."""
    payload = results[0] if len(results) == 1 else results
    return json.dumps(payload, indent=4)


def render_csv(results: list) -> str:
    """Return a CSV string with a header row."""
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELD_ORDER, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(results)
    return buf.getvalue()


# ── CLI entry point ──────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ip_info_extractor.py",
        description="🌐 IP Info Extractor – Powerful IP intelligence at your fingertips",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s                          look up your own public IP
  %(prog)s 8.8.8.8                  single IP lookup
  %(prog)s 8.8.8.8 1.1.1.1         batch lookup
  %(prog)s 8.8.8.8 --format csv    CSV output
  %(prog)s 8.8.8.8 -o result.json  save to file
        """,
    )
    parser.add_argument(
        "ips",
        nargs="*",
        metavar="IP",
        help="IP address(es) to look up (omit to detect your own public IP)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Save output to FILE instead of printing to stdout",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable coloured output",
    )
    args = parser.parse_args()

    # ── Resolve IPs ──────────────────────────────────────────────────────────
    if not args.ips:
        console.print("[bold cyan]No IP provided – detecting your own public IP…[/]")
        raw = fetch_own_ip()
        if raw.get("status") == "fail":
            console.print(f"[bold red]Error:[/] {raw.get('message')}")
            sys.exit(1)
        results = [enrich(raw)]
    else:
        results = lookup_ips(args.ips)

    if not results:
        sys.exit(1)

    # ── Render ────────────────────────────────────────────────────────────────
    if args.format == "table" and not args.output:
        render_table(results)
        return

    if args.format == "csv":
        text = render_csv(results)
    else:
        # json, or table-mode redirected to a file (falls back to JSON)
        text = render_json(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        console.print(f"[bold green]✔[/] Results saved to [bold]{args.output}[/]")
    else:
        console.print(text)


if __name__ == "__main__":
    main()
