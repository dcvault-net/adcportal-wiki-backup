#!/usr/bin/env python3
"""Render the missing wiki pages from the recovered dump (via local MediaWiki API)
into the ADCPortal archive's Vector-1.16 shell, so they flow through build_site_skin.py."""
import json, os, re, urllib.parse, urllib.request
from bs4 import BeautifulSoup

RAW  = r"D:\Projekte\archive_dc_network\raw"
WIKI = os.path.join(RAW, "wiki")
API  = "http://localhost:8899/api.php"
SHELL = os.path.join(WIKI, "ADC_Protocol.html")   # a real Wayback page as the structural shell

filemap = json.load(open(os.path.join(RAW, "filemap.json"), encoding="utf-8"))
have = set(filemap)                       # archive page names (underscored)

def api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    return json.loads(urllib.request.urlopen(url, timeout=60).read())

def all_pages(ns):
    out = []; cont = {}
    while True:
        d = api({"action": "query", "list": "allpages", "apnamespace": ns,
                 "aplimit": "500", "format": "json", **cont})
        out += [p["title"] for p in d["query"]["allpages"]]
        if "continue" in d: cont = d["continue"]
        else: break
    return out

# missing main-namespace articles (title uses spaces; archive uses underscores)
main = all_pages(0)
missing = [t for t in main if t.replace(" ", "_") not in have]
print(f"main articles in wiki: {len(main)} | missing from archive: {len(missing)}")

BAD = '<>:"/\\|?*'
safe = lambda s: ''.join('_' if c in BAD else c for c in s)

def rewrite_links(frag):
    """MediaWiki internal links -> /wiki/X (archive resolver handles them).
    MW 1.43 uses BOTH /index.php/Title (existing pages) and /index.php?title=Title&... (redlinks)."""
    for a in frag.find_all("a", href=True):
        h = a["href"]
        # strip the local MW server origin if present
        h2 = re.sub(r'^https?://localhost:8899', '', h)
        frag_id = "#" + h2.split("#", 1)[1] if ("#" in h2 and "/index.php" in h2) else ""
        title = None
        m = re.match(r'/index\.php/([^?#]+)', h2)                 # path form (existing pages)
        if m: title = urllib.parse.unquote(m.group(1))
        else:
            m2 = re.match(r'/index\.php\?title=([^&#]+)', h2)     # query form (redlinks/edit)
            if m2: title = urllib.parse.unquote(m2.group(1))
        if title:
            a["href"] = "/wiki/" + title.replace(" ", "_") + frag_id
            a.attrs.pop("class", None)   # drop MW 'new' redlink class; archive recomputes
    # images: MW has no uploads -> File: redlinks; archive marks them missing
    return frag

shell_html = open(SHELL, encoding="utf-8", errors="replace").read()
recovered = {}
for title in missing:
    name = title.replace(" ", "_")
    try:
        d = api({"action": "parse", "page": title, "prop": "text",
                 "formatversion": "2", "disablelimitreport": "1",
                 "disableeditsection": "1", "format": "json"})
        content = d["parse"]["text"]
    except Exception as e:
        print("  render fail", title, e); continue
    frag = BeautifulSoup(content, "html.parser")
    rewrite_links(frag)
    soup = BeautifulSoup(shell_html, "html.parser")
    fh = soup.select_one(".firstHeading")
    if fh: fh.clear(); fh.append(title)
    if soup.title: soup.title.string = f"{title} - ADCPortal Wiki"
    bc = soup.find(id="bodyContent")
    for c in list(bc.children): c.extract()
    bc.append(frag)
    fn = safe(name) + ".html"
    open(os.path.join(WIKI, fn), "w", encoding="utf-8").write(str(soup))
    recovered[name] = {"file": fn, "timestamp": "20110207000000", "url": "recovered-dump",
                       "group": "articles", "bytes": len(content), "source": "recovered"}
    print(f"  ok  {len(content):6d}  {fn}")

# merge into filemap (backup first)
if not os.path.exists(os.path.join(RAW, "filemap.pre-recovery.json")):
    json.dump(filemap, open(os.path.join(RAW, "filemap.pre-recovery.json"), "w", encoding="utf-8"), indent=1)
filemap.update(recovered)
json.dump(filemap, open(os.path.join(RAW, "filemap.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"\nrecovered pages rendered + added to filemap: {len(recovered)}")
print(f"filemap now: {len(filemap)} pages")
