#!/usr/bin/env python3
"""Fetch the one Talk page with a genuine Wayback 200 capture
(Talk:BLOM - Bloom Filter, 20110908212948) as a pristine id_ original,
and register it in filemap as a real archive capture (not a dump render)."""
import json, os, gzip, urllib.request

RAW  = r"D:\Projekte\archive_dc_network\raw"
WIKI = os.path.join(RAW, "wiki")

TS   = "20110908212948"
ORIG = "http://www.adcportal.com/wiki/Talk:BLOM_-_Bloom_Filter"
FILE = "Talk_BLOM_-_Bloom_Filter.html"
url  = f"https://web.archive.org/web/{TS}id_/{ORIG}"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (archive-rebuild)"})
data = urllib.request.urlopen(req, timeout=90).read()
if data[:2] == b"\x1f\x8b":                      # gzip-stored capture
    data = gzip.decompress(data)
html = data.decode("utf-8", "replace")
open(os.path.join(WIKI, FILE), "w", encoding="utf-8").write(html)

filemap = json.load(open(os.path.join(RAW, "filemap.json"), encoding="utf-8"))
filemap["Talk:BLOM_-_Bloom_Filter"] = {
    "file": FILE, "timestamp": TS, "url": ORIG, "group": "talk", "bytes": len(html),
}
json.dump(filemap, open(os.path.join(RAW, "filemap.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(f"saved {FILE} ({len(html)} bytes), timestamp {TS}")
print("filemap now:", len(filemap), "pages")
