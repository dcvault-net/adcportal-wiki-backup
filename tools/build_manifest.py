#!/usr/bin/env python3
"""Build a download manifest for the ADCPortal wiki from CDX data.
Pick the NEWEST status-200 capture per /wiki/ URL, categorize by namespace."""
import json, urllib.parse, urllib.request, collections, os, sys

CDX = ("http://web.archive.org/cdx/search/cdx?url=www.adcportal.com/wiki/*"
       "&output=json&filter=statuscode:200&fl=original,timestamp&limit=8000")

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (wiki archival research)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

rows = json.loads(fetch(CDX))[1:]

# newest 200 capture per urlkey (unquoted original path)
best = {}   # pagename -> (timestamp, original_url)
for orig, ts in rows:
    p = urllib.parse.urlparse(orig).path
    name = urllib.parse.unquote(p.split('/wiki/', 1)[-1])
    if not name:
        name = "Main_Page"  # bare /wiki/ -> index
    if name not in best or ts > best[name][0]:
        best[name] = (ts, orig)

NS_META = ('Special:', 'User:', 'Help:', 'Talk:', 'Template:', 'MediaWiki:',
           'ADCPortal_Wiki:', 'User_talk:', 'Category_talk:', 'File_talk:',
           'Template_talk:', 'Help_talk:')

articles, categories, files, meta = {}, {}, {}, {}
for name, (ts, orig) in best.items():
    if name.startswith('File:'):
        files[name] = (ts, orig)
    elif name.startswith('Category:'):
        categories[name] = (ts, orig)
    elif name.startswith(NS_META):
        meta[name] = (ts, orig)
    elif name.startswith('index.php'):
        pass  # skip raw script-path duplicates
    else:
        articles[name] = (ts, orig)

manifest = {"articles": articles, "categories": categories,
            "files": files, "meta": meta}
outdir = r"D:\Projekte\archive_dc_network\raw"
os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=1, ensure_ascii=False)

print(f"ARTICLES ({len(articles)}):")
for n in sorted(articles):
    print(f"   {articles[n][0]}  {n}")
print(f"\nCATEGORIES ({len(categories)}) | FILE-pages ({len(files)}) | META/ns ({len(meta)})")
print(f"\nmanifest.json written to {outdir}")
