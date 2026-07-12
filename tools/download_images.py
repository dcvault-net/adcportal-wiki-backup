#!/usr/bin/env python3
"""Download referenced /mediawiki/ images as pristine originals, best-200 per URL."""
import os, json, time, urllib.parse, urllib.request, urllib.error

RAW=r"D:\Projekte\archive_dc_network\raw"
IMGDIR=os.path.join(RAW,"images")
scan=json.load(open(os.path.join(RAW,"linkscan.json"),encoding="utf-8"))
wanted=scan["images"]   # list of /mediawiki/... paths

def cdx(pattern):
    url=("http://web.archive.org/cdx/search/cdx?url=www.adcportal.com"+pattern+
         "&output=json&filter=statuscode:200&fl=original,timestamp&limit=9000")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req,timeout=90).read())[1:]

# build newest-200 timestamp map keyed by unquoted path
best={}
for pat in ("/mediawiki/images/*","/mediawiki/skins/*"):
    for orig,ts in cdx(pat):
        path=urllib.parse.urlparse(orig).path
        if path not in best or ts>best[path][0]:
            best[path]=(ts,orig)
    time.sleep(1)

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (wiki archival research)"})
    return urllib.request.urlopen(req,timeout=90).read()

imgmap={}; missing=[]
for path in wanted:
    dec=urllib.parse.unquote(path)
    if dec not in best:
        missing.append(path); print("  no200  ",path); continue
    ts,orig=best[dec]
    local=path.lstrip("/")               # keep mediawiki/images/... structure
    dest=os.path.join(RAW,*local.split("/"))
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    url=f"http://web.archive.org/web/{ts}id_/{orig}"
    ok=False
    for attempt in range(4):
        try:
            data=fetch(url)
            open(dest,"wb").write(data)
            imgmap[path]={"local":local,"timestamp":ts,"bytes":len(data)}
            print(f"  ok {len(data):7d}  {local}"); ok=True; break
        except Exception as e:
            time.sleep(2.5)
    if not ok:
        missing.append(path); print("  FAIL   ",path)
    time.sleep(0.5)

json.dump({"images":imgmap,"missing":missing},
          open(os.path.join(RAW,"imagemap.json"),"w",encoding="utf-8"),indent=1,ensure_ascii=False)
print(f"\nimages ok: {len(imgmap)} | missing: {len(missing)}")
if missing: print("missing:",missing)
