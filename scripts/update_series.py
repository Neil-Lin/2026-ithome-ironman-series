#!/usr/bin/env python3
import html, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / "config.json").read_text())
base = config["source"]
groups = config["groups"]
series = {}
errors = []

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def fetch(url):
    request = Request(url, headers={"User-Agent":"2026-ithome-ironman-series/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")

for page in range(1, 80):
    url = base if page == 1 else f"{base}?page={page}"
    try:
        body = fetch(url)
    except Exception as error:
        errors.append({"page": page, "error": str(error)})
        break
    found = list(re.finditer(r'<a[^>]+href=["\']([^"\']*/users/\d+/ironman/\d+)[^"\']*["\'][^>]*>(.*?)</a>', body, re.I | re.S))
    for match in found:
        link = urljoin(base, html.unescape(match.group(1)))
        title = clean(match.group(2))
        if not title or link in series: continue
        before = body[max(0, match.start() - 1800):match.start()]
        group_hits = [group for group in groups if group in clean(before)]
        series[link] = {"id": link.rsplit("/", 1)[-1].split("?", 1)[0], "title": title, "url": link, "group": group_hits[-1] if group_hits else "未分類"}
    if not re.search(r'href=["\'][^"\']*[?&]page=%d(?:["\'&])' % (page + 1), body, re.I):
        break

items = sorted(series.values(), key=lambda item: (item["group"], item["title"]))
(ROOT / "data" / "series.json").write_text(json.dumps({"updatedAt": datetime.now(timezone.utc).isoformat(), "count": len(items), "errors": errors, "series": items}, ensure_ascii=False, indent=2) + "\n")
print(f"saved {len(items)} series; {len(errors)} errors")
