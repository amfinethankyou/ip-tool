<h1 align="center">
  <br>
  🌐 IP Info Extractor
  <br>
</h1>

<p align="center">
  <b>Powerful IP intelligence at your fingertips — straight from the terminal.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/License-MIT-green?logo=opensourceinitiative&logoColor=white" alt="MIT License"/>
  <img src="https://img.shields.io/badge/API-ip--api.com-orange" alt="ip-api.com"/>
  <img src="https://img.shields.io/badge/Output-Table%20%7C%20JSON%20%7C%20CSV-purple" alt="Output formats"/>
</p>

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔍 **Single & Batch Lookups** | Look up one IP or hundreds at once |
| 🏠 **Own-IP Detection** | Run with no arguments to discover your own public IP |
| 🌈 **Rich Coloured Tables** | Beautiful terminal output powered by [Rich](https://github.com/Textualize/rich) |
| 📄 **Multiple Output Formats** | `table` (default), `json`, or `csv` |
| 💾 **Save to File** | Write results to any file with `--output` |
| 🛡️ **Proxy / VPN / Hosting Flags** | Instantly know if an IP belongs to a VPN, proxy, or data-centre |
| 📡 **Reverse DNS** | PTR record lookup for every IP |
| ✅ **Input Validation** | Invalid IPs are skipped gracefully with a clear error |
| ⏱️ **Timeout Handling** | Never hangs — all requests have a configurable timeout |

---

## 🚀 Quick Start

### Prerequisites

```bash
sudo apt-get install python3 python3-pip   # Debian / Ubuntu
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Make the script executable *(optional)*

```bash
chmod +x ip_info_extractor.py
```

---

## 📖 Usage

```
usage: ip_info_extractor.py [-h] [--format {table,json,csv}] [--output FILE] [--no-color] [IP ...]

🌐 IP Info Extractor – Powerful IP intelligence at your fingertips

positional arguments:
  IP                    IP address(es) to look up (omit to detect your own public IP)

options:
  -h, --help            show this help message and exit
  --format/-f {table,json,csv}
                        Output format (default: table)
  --output, -o FILE     Save output to FILE instead of printing to stdout
  --no-color            Disable coloured output
```

---

## 💡 Examples

### Look up your own public IP

```bash
python3 ip_info_extractor.py
```

### Single IP lookup

```bash
python3 ip_info_extractor.py 8.8.8.8
```

```
╭─────────────────────────────────────────────────────╮
│       IP Intelligence Report  •  8.8.8.8            │
├────────────────────┬────────────────────────────────┤
│ Field              │ Value                          │
├────────────────────┼────────────────────────────────┤
│ IP Address         │ 8.8.8.8                        │
│ Country            │ United States                  │
│ Country Code       │ US                             │
│ Region             │ California                     │
│ City               │ Mountain View                  │
│ ZIP                │ 94043                          │
│ Latitude           │ 37.422                         │
│ Longitude          │ -122.0841                      │
│ ISP                │ Google LLC                     │
│ Organization       │ Google LLC                     │
│ AS Number          │ AS15169 Google LLC             │
│ Timezone           │ America/Los_Angeles            │
│ Mobile Network     │ No                             │
│ Proxy / VPN        │ No                             │
│ Hosting / DC       │ Yes                            │
│ Reverse DNS        │ dns.google                     │
╰────────────────────┴────────────────────────────────╯
```

### Batch lookup (multiple IPs)

```bash
python3 ip_info_extractor.py 8.8.8.8 1.1.1.1 9.9.9.9
```

### JSON output

```bash
python3 ip_info_extractor.py 8.8.8.8 --format json
```

```json
{
    "query": "8.8.8.8",
    "country": "United States",
    "countryCode": "US",
    "regionName": "California",
    "city": "Mountain View",
    "zip": "94043",
    "lat": 37.422,
    "lon": -122.0841,
    "isp": "Google LLC",
    "org": "Google LLC",
    "as": "AS15169 Google LLC",
    "timezone": "America/Los_Angeles",
    "mobile": "No",
    "proxy": "No",
    "hosting": "Yes",
    "rdns": "dns.google"
}
```

### CSV output

```bash
python3 ip_info_extractor.py 8.8.8.8 1.1.1.1 --format csv
```

### Save results to a file

```bash
python3 ip_info_extractor.py 8.8.8.8 --format json --output result.json
python3 ip_info_extractor.py 8.8.8.8 1.1.1.1 --format csv  --output results.csv
```

### Plain output (no colour, useful for piping)

```bash
python3 ip_info_extractor.py 8.8.8.8 --format json --no-color | jq .
```

---

## 🗂️ Repository Structure

```
ip-tool/
├── ip_info_extractor.py   # Main tool
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

## 🔌 API

This tool uses the free tier of [ip-api.com](https://ip-api.com).

> **Note:** The free tier is limited to **45 requests/minute**. For higher
> throughput, see the [ip-api.com Pro plan](https://ip-api.com/docs/pro).

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| [requests](https://pypi.org/project/requests/) | HTTP client |
| [rich](https://pypi.org/project/rich/) | Coloured terminal output |

---

## 📄 License

This project is released under the **MIT License** — do whatever you like with it.
