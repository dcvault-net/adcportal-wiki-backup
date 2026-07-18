#!/usr/bin/env python3
"""Render the Talk-namespace pages from the recovered dump (via local MediaWiki API)
into the ADCPortal archive shell, so the article Discussion tabs resolve.

Talk:BLOM - Bloom Filter is skipped here: it has a genuine Wayback 200 capture
(fetched by fetch_talk_blom.py) and that authentic copy is used instead."""
import json, os, re, urllib.parse, urllib.request
from bs4 import BeautifulSoup

RAW  = r"D:\Projekte\archive_dc_network\raw"
WIKI = os.path.join(RAW, "wiki")
API  = "http://localhost:8899/api.php"
SHELL = os.path.join(WIKI, "ADC_Protocol.html")   # a real Wayback page as the structural shell

# talk pages that come from the Internet Archive, not the dump render
FROM_WAYBACK = {"Talk:BLOM - Bloom Filter"}

# talk pages in adjacent namespaces (their subject pages -- User:/Template: -- are
# not rendered, so these are reachable only by direct URL). Rendered on request.
EXTRA_TALK = ["User talk:Pietry", "Template talk:Infobox Extension"]

filemap = json.load(open(os.path.join(RAW, "filemap.json"), encoding="utf-8"))

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

talk = [t for t in all_pages(1) if t not in FROM_WAYBACK] + EXTRA_TALK
talk = [t for t in talk if t.replace(" ", "_") not in filemap]   # skip already-rendered
print(f"talk pages to render: {len(talk)}  ->  {talk}")

BAD = '<>:"/\\|?*'
safe = lambda s: ''.join('_' if c in BAD else c for c in s)

def rewrite_links(frag):
    """MediaWiki internal links -> /wiki/X (the build resolver handles them).
    MW 1.43 uses BOTH /index.php/Title (existing) and /index.php?title=Title (redlinks)."""
    for a in frag.find_all("a", href=True):
        h = a["href"]
        h2 = re.sub(r'^https?://localhost:8899', '', h)
        frag_id = "#" + h2.split("#", 1)[1] if ("#" in h2 and "/index.php" in h2) else ""
        title = None
        m = re.match(r'/index\.php/([^?#]+)', h2)
        if m: title = urllib.parse.unquote(m.group(1))
        else:
            m2 = re.match(r'/index\.php\?title=([^&#]+)', h2)
            if m2: title = urllib.parse.unquote(m2.group(1))
        if title:
            a["href"] = "/wiki/" + title.replace(" ", "_") + frag_id
            a.attrs.pop("class", None)
    return frag

shell_html = open(SHELL, encoding="utf-8", errors="replace").read()
added = {}
for title in talk:
    name = title.replace(" ", "_")            # keeps the "Talk:" colon
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
    if fh: fh.clear(); fh.append(title)       # e.g. "Talk:Compliancy list"
    if soup.title: soup.title.string = f"{title} - ADCPortal Wiki"
    bc = soup.find(id="bodyContent")
    for c in list(bc.children): c.extract()
    bc.append(frag)
    fn = safe(name) + ".html"
    open(os.path.join(WIKI, fn), "w", encoding="utf-8").write(str(soup))
    added[name] = {"file": fn, "timestamp": "20110207000000", "url": "recovered-dump",
                   "group": "talk", "bytes": len(content), "source": "recovered"}
    print(f"  ok  {len(content):6d}  {fn}")

filemap.update(added)
json.dump(filemap, open(os.path.join(RAW, "filemap.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(f"\ntalk pages rendered + added to filemap: {len(added)}")
print(f"filemap now: {len(filemap)} pages")
