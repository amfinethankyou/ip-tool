#!/usr/bin/env python3
"""
IP Info Extractor - Powerful IP intelligence at your fingertips.

Supports single and batch lookups, multiple output formats (table / JSON / CSV),
automatic own-IP detection, reverse-DNS, and proxy/VPN/hosting/mobile flags.
"""

import argparse
import csv
import ipaddress
import json
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import requests
from rich import box
from rich.console import Console
from rich.table import Table

# -- API configuration --------------------------------------------------------

BATCH_API_URL = "http://ip-api.com/batch"
SINGLE_API_URL = "http://ip-api.com/json/{ip}"
OWN_IP_API_URL = "http://ip-api.com/json/"
DEFAULT_REQUEST_TIMEOUT = 10.0
DEFAULT_REQUEST_RETRIES = 2
MAX_BATCH_SIZE = 100
REVERSE_DNS_WORKERS = 16

# Fields requested from the API (includes paid flags available in the free tier)
API_FIELDS = (
    "query,status,message,country,countryCode,regionName,city,"
    "zip,lat,lon,isp,org,as,timezone,mobile,proxy,hosting"
)

# Display order and labels for output
FIELD_ORDER = [
    "query",
    "country",
    "countryCode",
    "regionName",
    "city",
    "zip",
    "lat",
    "lon",
    "isp",
    "org",
    "as",
    "timezone",
    "mobile",
    "proxy",
    "hosting",
    "rdns",
]

FIELD_LABELS = {
    "query": "IP Address",
    "country": "Country",
    "countryCode": "Country Code",
    "regionName": "Region",
    "city": "City",
    "zip": "ZIP",
    "lat": "Latitude",
    "lon": "Longitude",
    "isp": "ISP",
    "org": "Organization",
    "as": "AS Number",
    "timezone": "Timezone",
    "mobile": "Mobile Network",
    "proxy": "Proxy / VPN",
    "hosting": "Hosting / DC",
    "rdns": "Reverse DNS",
}

session = requests.Session()
session.headers.update({"User-Agent": "ip-info-extractor/1.1"})
console = Console()


# -- Helpers -----------------------------------------------------------------

def validate_ip(ip: str) -> bool:
    """Return True if ip is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def load_ips_from_file(path: str) -> list[str]:
    """Load IPs from a file, accepting whitespace/comma-separated values."""
    ips: list[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            for token in line.replace(",", " ").split():
                ips.append(token.strip())
    return ips


def split_valid_invalid(ips: list[str]) -> tuple[list[str], list[str]]:
    """Split input IP list into unique valid and invalid entries."""
    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()

    for ip in ips:
        if ip in seen:
            continue
        seen.add(ip)
        if validate_ip(ip):
            valid.append(ip)
        else:
            invalid.append(ip)
    return valid, invalid


def reverse_dns(ip: str) -> str:
    """Return the PTR record for ip, or N/A if none exists."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return "N/A"


def normalize_flags(data: dict) -> dict:
    """Normalize boolean/mobile/proxy/hosting fields to Yes/No strings."""
    data["mobile"] = "Yes" if data.get("mobile") else "No"
    data["proxy"] = "Yes" if data.get("proxy") else "No"
    data["hosting"] = "Yes" if data.get("hosting") else "No"
    return data


def add_reverse_dns(results: list[dict]) -> None:
    """Resolve reverse DNS for result list in parallel for speed."""
    if not results:
        return

    ips = [str(item.get("query", "")) for item in results]
    workers = min(REVERSE_DNS_WORKERS, max(1, len(ips)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        ptr_records = list(executor.map(reverse_dns, ips))

    for item, rdns in zip(results, ptr_records):
        item["rdns"] = rdns


# -- Network layer ------------------------------------------------------------

def _abort(message: str) -> None:
    """Print an error and exit."""
    console.print(f"[bold red]Error:[/] {message}")
    sys.exit(1)


def _request_json(
    method: str,
    url: str,
    timeout: float,
    retries: int,
    params: dict | None = None,
    payload: list[dict] | dict | None = None,
) -> dict | list:
    """Perform a JSON HTTP request with small retry backoff."""
    for attempt in range(retries + 1):
        try:
            response = session.request(
                method=method,
                url=url,
                params=params,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as exc:
            if attempt < retries:
                time.sleep(0.5 * (2**attempt))
                continue
            _abort(f"Request timed out after {retries + 1} attempt(s): {exc}")
        except requests.exceptions.RequestException as exc:
            if attempt < retries:
                time.sleep(0.5 * (2**attempt))
                continue
            _abort(f"Network error: {exc}")
        except ValueError as exc:
            _abort(f"Invalid JSON response from API: {exc}")

    _abort("Unknown request failure.")
    return {}


def fetch_single(ip: str, timeout: float, retries: int) -> dict:
    """Fetch geo-data for a single IP address."""
    return _request_json(
        method="GET",
        url=SINGLE_API_URL.format(ip=ip),
        timeout=timeout,
        retries=retries,
        params={"fields": API_FIELDS},
    )


def fetch_own_ip(timeout: float, retries: int) -> dict:
    """Fetch geo-data for the machine's own public IP."""
    return _request_json(
        method="GET",
        url=OWN_IP_API_URL,
        timeout=timeout,
        retries=retries,
        params={"fields": API_FIELDS},
    )


def fetch_batch(ips: list[str], timeout: float, retries: int) -> list[dict]:
    """Fetch geo-data for up to 100 IPs in one HTTP call."""
    payload = [{"query": ip} for ip in ips]
    response = _request_json(
        method="POST",
        url=BATCH_API_URL,
        timeout=timeout,
        retries=retries,
        params={"fields": API_FIELDS},
        payload=payload,
    )
    return response if isinstance(response, list) else []


def lookup_ips(ips: list[str], timeout: float, retries: int) -> list[dict]:
    """Validate, fetch and enrich data for a list of IP strings."""
    valid, invalid = split_valid_invalid(ips)

    for ip in invalid:
        console.print(f"[bold red]Invalid IP:[/] '{ip}' - skipped.")

    if not valid:
        return []

    raw: list[dict] = []
    # Batch in chunks of 100 (API limit); use single endpoint for lone IPs.
    for index in range(0, len(valid), MAX_BATCH_SIZE):
        chunk = valid[index : index + MAX_BATCH_SIZE]
        if len(chunk) == 1:
            raw.append(fetch_single(chunk[0], timeout=timeout, retries=retries))
        else:
            raw.extend(fetch_batch(chunk, timeout=timeout, retries=retries))

    results: list[dict] = []
    for data in raw:
        if data.get("status") == "fail":
            console.print(
                f"[bold red]Lookup failed for {data.get('query', '?')}:[/] "
                f"{data.get('message', 'Unknown error')}"
            )
            continue
        results.append(normalize_flags(data))

    add_reverse_dns(results)
    return results


# -- Output renderers ---------------------------------------------------------

def render_table(results: list[dict], out_console: Console | None = None) -> None:
    """Pretty-print each result as a Rich table."""
    target = out_console or console
    for data in results:
        table = Table(
            title=(
                f"[bold cyan]IP Intelligence Report[/]  [dim]*[/]  "
                f"[bold yellow]{data['query']}[/]"
            ),
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            border_style="cyan",
            min_width=54,
        )
        table.add_column("Field", style="bold green", min_width=18)
        table.add_column("Value", style="white", min_width=28)

        for key in FIELD_ORDER:
            label = FIELD_LABELS.get(key, key)
            value = str(data.get(key, "N/A"))
            # Highlight security-relevant flags.
            if key in ("proxy", "mobile", "hosting") and value == "Yes":
                value = f"[bold yellow]{value}[/]"
            table.add_row(label, value)

        target.print(table)
        target.print()


def render_json(results: list[dict]) -> str:
    """Return a JSON string (single object for one result, array otherwise)."""
    payload = results[0] if len(results) == 1 else results
    return json.dumps(payload, indent=4)


def render_csv(results: list[dict]) -> str:
    """Return a CSV string with a header row."""
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=FIELD_ORDER,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(results)
    return buffer.getvalue()


def write_output(path: str, text: str) -> None:
    """Write output to file with clear error reporting."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        _abort(f"Could not write output file '{path}': {exc}")


# -- CLI entry point ----------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ip_info_extractor.py",
        description="IP Info Extractor - Powerful IP intelligence at your fingertips",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s                                   look up your own public IP
  %(prog)s 8.8.8.8                           single IP lookup
  %(prog)s 8.8.8.8 1.1.1.1                  batch lookup
  %(prog)s --input-file ips.txt --format csv read IPs from file
  %(prog)s 8.8.8.8 --timeout 5 --retries 3   tune network behavior
  %(prog)s 8.8.8.8 -o result.json            save to file
        """,
    )
    parser.add_argument(
        "ips",
        nargs="*",
        metavar="IP",
        help="IP address(es) to look up (omit to detect your own public IP)",
    )
    parser.add_argument(
        "--input-file",
        "-i",
        metavar="FILE",
        help="Read IP address(es) from FILE (one per line or comma-separated)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Save output to FILE instead of printing to stdout",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_REQUEST_TIMEOUT})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_REQUEST_RETRIES,
        help=f"Request retries on failure (default: {DEFAULT_REQUEST_RETRIES})",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable coloured output",
    )
    args = parser.parse_args()

    if args.timeout <= 0:
        _abort("--timeout must be greater than 0")
    if args.retries < 0:
        _abort("--retries cannot be negative")

    global console
    console = Console(no_color=args.no_color)

    source_ips: list[str] = []
    if args.input_file:
        try:
            source_ips.extend(load_ips_from_file(args.input_file))
        except OSError as exc:
            _abort(f"Could not read input file '{args.input_file}': {exc}")

    if args.ips:
        source_ips.extend(args.ips)

    # -- Resolve IPs ----------------------------------------------------------
    if not source_ips:
        console.print("[bold cyan]No IP provided - detecting your own public IP...[/]")
        raw = fetch_own_ip(timeout=args.timeout, retries=args.retries)
        if raw.get("status") == "fail":
            _abort(str(raw.get("message", "Unknown API error")))
        results = [normalize_flags(raw)]
        add_reverse_dns(results)
    else:
        results = lookup_ips(source_ips, timeout=args.timeout, retries=args.retries)

    if not results:
        sys.exit(1)

    # -- Render ---------------------------------------------------------------
    if args.format == "table" and not args.output:
        render_table(results)
        return

    if args.format == "csv":
        text = render_csv(results)
    elif args.format == "table":
        capture_console = Console(record=True, no_color=True, width=120)
        render_table(results, out_console=capture_console)
        text = capture_console.export_text()
    else:
        text = render_json(results)

    if args.output:
        write_output(args.output, text)
        console.print(f"[bold green]OK[/] Results saved to [bold]{args.output}[/]")
    else:
        console.print(text)


if __name__ == "__main__":
    main()
