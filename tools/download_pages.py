#!/usr/bin/env python3
"""Download best-200 captures of ADCPortal wiki pages as pristine originals (id_ endpoint)."""
import json, os, time, urllib.request, urllib.error

RAW = r"D:\Projekte\archive_dc_network\raw"
OUT = os.path.join(RAW, "wiki")
os.makedirs(OUT, exist_ok=True)
manifest = json.load(open(os.path.join(RAW, "manifest.json"), encoding="utf-8"))

BAD = '<>:"/\\|?*'
def safe(name):
    return ''.join('_' if c in BAD else c for c in name)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (wiki archival research)"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

# download articles + categories (skip File: html and meta for now)
groups = {"articles": manifest["articles"], "categories": manifest["categories"]}
filemap = {}
errors = []
n = 0
for group, pages in groups.items():
    for name, (ts, orig) in sorted(pages.items()):
        n += 1
        fn = safe(name) + ".html"
        url = f"http://web.archive.org/web/{ts}id_/{orig}"
        try:
            data = fetch(url)
            with open(os.path.join(OUT, fn), "wb") as f:
                f.write(data)
            filemap[name] = {"file": fn, "timestamp": ts, "url": orig,
                             "group": group, "bytes": len(data)}
            print(f"  ok  {len(data):6d}  {fn}")
        except urllib.error.HTTPError as e:
            errors.append((name, e.code)); print(f"  ERR {e.code}     {fn}")
        except Exception as e:
            errors.append((name, str(e))); print(f"  ERR {e}  {fn}")
        time.sleep(0.4)

json.dump(filemap, open(os.path.join(RAW, "filemap.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(f"\ndownloaded {len(filemap)} pages, {len(errors)} errors")
if errors:
    print("errors:", errors)
