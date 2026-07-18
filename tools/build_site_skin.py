#!/usr/bin/env python3
"""Reconstruct the wiki keeping the ORIGINAL MediaWiki Vector skin (recovered CSS)."""
import os, re, json, shutil, urllib.parse, collections
from bs4 import BeautifulSoup

RAW  = r"D:\Projekte\archive_dc_network\raw"
SITE = r"D:\Projekte\archive_dc_network\site"
WIKI = os.path.join(RAW, "wiki")
SCRATCH = os.path.dirname(os.path.abspath(__file__))

filemap = json.load(open(os.path.join(RAW, "filemap.json"), encoding="utf-8"))
name2file = {name: meta["file"] for name, meta in filemap.items()}
name2file["Main_Page"] = "index.html"

# MediaWiki titles are case-sensitive after the first letter (so "Flexhub" and
# "FlexHub" are different pages, usually an article + a #REDIRECT to it), but a
# static site on a case-insensitive host cannot keep two files that differ only in
# case. Collapse each such collision onto one canonical file and route every
# colliding name to it: prefer a genuine Wayback capture, then the larger page
# (the real article over a tiny redirect stub).
_groups = collections.defaultdict(list)
for _nm, _meta in filemap.items():
    _groups[_meta["file"].lower()].append(_nm)
write_names = set(filemap)
for _low, _names in _groups.items():
    if len(_names) == 1:
        continue
    _winner = max(_names, key=lambda n: (0 if filemap[n].get("source") == "recovered" else 1,
                                         filemap[n].get("bytes", 0)))
    _win_file = filemap[_winner]["file"]
    for _nm in _names:
        name2file[_nm] = _win_file
        if _nm != _winner:
            write_names.discard(_nm)

lower2name = {k.lower(): k for k in name2file}

present_images = set()
for root, _, files in os.walk(os.path.join(RAW, "mediawiki")):
    for f in files:
        rel = os.path.relpath(os.path.join(root, f), RAW).replace("\\", "/")
        present_images.add("/" + urllib.parse.unquote(rel))

META_NS = ("Special:", "User:", "User_talk:", "Help:", "Talk:", "MediaWiki:",
           "Template:", "Template_talk:", "ADCPortal_Wiki:", "Category_talk:",
           "File_talk:", "Help_talk:", "Media:")
stats = collections.Counter()

REDIRECTS = (
    "# Map original MediaWiki URLs to the static files.\n"
    "# Colon-namespaced pages (Special:/Category:) use \"_\" in the static filename.\n"
    "/wiki/Special:*    /Special_:splat    301\n"
    "/wiki/Category:*   /Category_:splat   301\n"
    "/wiki/Talk:*       /Talk_:splat       301\n"
    "/wiki/User_talk:*      /User_talk_:splat      301\n"
    "/wiki/Template_talk:*  /Template_talk_:splat  301\n"
    "/Special:*         /Special_:splat    301\n"
    "/Category:*        /Category_:splat   301\n"
    "/Talk:*            /Talk_:splat       301\n"
    "/User_talk:*           /User_talk_:splat      301\n"
    "/Template_talk:*       /Template_talk_:splat  301\n"
    "/wiki/Main_Page    /                  301\n"
    "/wiki              /                  301\n"
    "/wiki/*            /:splat            301\n"
)

ARCHIVE_NOTE = (
    'This is a static archive of the ADCPortal wiki. It was reconstructed from '
    'all available <a href="https://web.archive.org/">Internet Archive</a> '
    'snapshots and merged into the most complete version possible. Links to '
    'pages that were never captured by the archive are shown in '
    '<span class="na">red</span> and cannot be opened.'
)
RECOVERED_NOTE = (
    'This page was recovered from a community database backup of the ADCPortal wiki '
    '(the original wikitext, rendered back to HTML). It was never captured by the '
    'Internet Archive. Images are not part of that backup, and links to pages that '
    'are still missing are inactive.'
)

# titles that changed between the recovered dump (Feb 2011) and the Wayback capture (Sep 2011)
ALIASES = {
    "Code_Example:Blom": "Code_Example_Blom",
    "Code_Example:_Blom": "Code_Example_Blom",
}

def resolve_page(target):
    t = urllib.parse.unquote(target).replace(" ", "_")
    t = ALIASES.get(t, t)
    if t in name2file: return name2file[t]
    if t.lower() in lower2name: return name2file[lower2name[t.lower()]]
    if ":" in t: return None   # namespaced pages (Special:/File:/Category:) resolve by exact match only
    cands = [k for k in name2file if k.split("_-_")[0].lower() == t.lower()]
    if len(cands) == 1: return name2file[cands[0]]
    base = t.split("_-_")[0]
    if base in name2file: return name2file[base]
    if base.lower() in lower2name: return name2file[lower2name[base.lower()]]
    return None

def local_asset(url):
    """Rewrite /mediawiki/... or /misc/... to a relative local path if present."""
    path = urllib.parse.urlparse(url).path
    key = urllib.parse.unquote(path)
    if key in present_images:
        return path.lstrip("/")
    return None

def process(path, name, out_name):
    soup = BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "html.parser")
    head = soup.head
    ts = filemap[name]["timestamp"]

    # drop scripts and all original stylesheet/favicon links
    for s in soup.find_all("script"):
        s.decompose()
    for l in head.find_all("link"):
        rel = " ".join(l.get("rel") or [])
        if "stylesheet" in rel or "icon" in rel or "search" in rel or "alternate" in rel:
            l.decompose()
    for b in head.find_all("base"):
        b.decompose()

    # inject recovered local stylesheets in the original screen load order,
    # with our small overrides last
    css_chain = [
        ("mediawiki/skins/vector/main-ltr.css", "screen"),
        ("mediawiki/skins/common/shared.css", "screen"),
        ("mediawiki/site-common.css", "all"),
        ("mediawiki/site-vector.css", "all"),
        ("mediawiki/gen.css", "all"),
        ("overrides.css", "all"),
    ]
    for href, media in css_chain:
        if not os.path.exists(os.path.join(SITE, *href.split("/"))):
            continue
        link = soup.new_tag("link", rel="stylesheet", href=href)
        link["media"] = media
        head.append(link)

    # logo
    logo = soup.select_one("#p-logo a")
    if logo:
        st = logo.get("style", "")
        st = re.sub(r'url\((?:https?:)?[^)]*\)', 'url(misc/wiki_logo.png)', st)
        logo["style"] = st
        logo["href"] = "index.html"
        logo.attrs.pop("title", None)

    body_content = soup.find(id="bodyContent")

    # namespace tabs (Page / Discussion / Read): genuine captures already carry the
    # right hrefs, but recovered pages inherited the shell page's tabs (ADC_Protocol),
    # so recompute them from this page's own name. The link loop below then resolves
    # the /wiki/ targets to local files or marks them inert.
    if filemap.get(name, {}).get("source") == "recovered":
        # map a talk-namespace prefix to its subject-namespace prefix (keys use "_"
        # for the space inside two-word namespaces, e.g. "User_talk:")
        TALK_TO_SUBJECT = {
            "Talk:": "", "User_talk:": "User:", "Template_talk:": "Template:",
            "Category_talk:": "Category:", "Help_talk:": "Help:", "File_talk:": "File:",
            "MediaWiki_talk:": "MediaWiki:", "Project_talk:": "Project:",
        }
        is_talk = False
        subject = name
        talk_target = "Talk:" + name           # a subject page's talk lives at Talk:<name>
        for _tp, _sp in TALK_TO_SUBJECT.items():
            if name.startswith(_tp):
                is_talk = True
                subject = _sp + name[len(_tp):]  # e.g. User_talk:Pietry -> User:Pietry
                talk_target = name               # this page IS the talk page
                break

        def set_tab(tab_id, href, selected, keep_new=False):
            li = soup.find(id=tab_id)
            if not li:
                return
            a = li.find("a")
            if a:
                a["href"] = href
                a.attrs.pop("class", None)   # drop stale 'new'/inert; loop recomputes
                a.attrs.pop("title", None)
            cls = [c for c in (li.get("class") or []) if c not in ("selected", "new")]
            if keep_new:
                cls.append("new")            # let the loop clear it iff the link resolves
            if selected:
                cls.append("selected")
            li["class"] = cls

        set_tab("ca-nstab-main", "/wiki/" + subject, not is_talk)
        set_tab("ca-talk", "/wiki/" + talk_target, is_talk, keep_new=True)
        set_tab("ca-view", "/wiki/" + name, True)

    def in_content(el):
        p = el
        while p is not None:
            if getattr(p, "get", None) and p.get("id") == "bodyContent":
                return True
            p = p.parent
        return False

    # images
    for img in list(soup.find_all("img")):
        src = img.get("src", "")
        if src.startswith(("/mediawiki/", "/misc/")):
            loc = local_asset(src)
            if loc:
                img["src"] = loc
                img.attrs.pop("srcset", None)
                stats["img_ok"] += 1
            elif in_content(img):
                alt = (img.get("alt") or "").strip()
                span = soup.new_tag("span"); span["class"] = "noimg"
                span["title"] = "Image not archived"
                span.string = alt if alt else "▢"
                img.replace_with(span); stats["img_missing"] += 1
            else:
                img.decompose(); stats["img_chrome_dropped"] += 1
        elif src.startswith("http"):
            img.decompose()  # off-site / wayback pixels

    # unwrap image links (keep the <img>/placeholder, drop the dead File: link)
    for a in soup.find_all("a", class_="image"):
        a.replace_with(*a.contents)

    # links -- resolve to a local page where possible; otherwise keep the
    # ORIGINAL colour/class (blue link or red .new redlink) and make it inert
    # with an English tooltip. This matches the original appearance.
    def clear_tab_new(anchor):
        # a namespace tab that now resolves must lose the red 'new' class on its <li>
        li = anchor.find_parent("li")
        if li and li.get("class"):
            li["class"] = [c for c in li["class"] if c != "new"]

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/wiki/"):
            rest = href[len("/wiki/"):]; frag = ""
            if "#" in rest: rest, frag = rest.split("#", 1)
            page = urllib.parse.unquote(rest)
            target = resolve_page(page)   # resolves recovered Special:/Category: pages too
            if target:
                a["href"] = target + (("#" + frag) if frag else "")
                a.attrs.pop("title", None)
                if a.get("class"): a.attrs.pop("class", None)
                clear_tab_new(a)
                stats["link_ok"] += 1
            else:
                a["href"] = "#"
                a["class"] = (a.get("class") or []) + ["archived-inert"]
                a["title"] = "Page not archived"
                stats["link_inert"] += 1
        elif href.startswith(("/mediawiki/", "/index.php", "/misc/")):
            # a redlink whose page now exists (e.g. a Discussion tab pointing at a
            # talk page we recovered) -> wire it up instead of killing it
            promoted = None
            if "redlink" in href:
                q = urllib.parse.urlparse(href.replace("&amp;", "&")).query
                qs = urllib.parse.parse_qs(q)
                if "title" in qs:
                    promoted = resolve_page(qs["title"][0])
            if promoted:
                a["href"] = promoted
                a.attrs.pop("title", None)
                a.attrs.pop("class", None)
                clear_tab_new(a)
                stats["link_ok"] += 1
            else:
                a["href"] = "#"
                a["class"] = (a.get("class") or []) + ["archived-inert"]
                a["title"] = "Not available in this archive"
                stats["link_inert"] += 1
        elif href.startswith("//"):
            a["href"] = "https:" + href
        elif href.startswith("http://web.archive.org"):
            m = re.search(r"/https?://(.+)$", href); a["href"] = ("https://" + m.group(1)) if m else "#"
        # external http(s) + #anchors: keep

    # disable search form
    for form in soup.find_all("form"):
        form["action"] = "#"; form["onsubmit"] = "return false"

    # wrap wide tables (content only, not infobox)
    if body_content:
        for table in body_content.find_all("table"):
            cls = table.get("class") or []
            if "infobox" in cls or table.find_parent("table") is not None:
                continue
            w = soup.new_tag("div"); w["class"] = "table-scroll"
            table.wrap(w); stats["table_wrapped"] += 1

    # add the reconstruction note at the top of the original footer
    footer = soup.find(id="footer")
    if footer:
        note_html = RECOVERED_NOTE if filemap.get(name, {}).get("source") == "recovered" else ARCHIVE_NOTE
        note = soup.new_tag("div"); note["class"] = "archive-note"
        note.append(BeautifulSoup(note_html, "html.parser"))
        footer.insert(0, note)
        stats["footer_note"] += 1

    with open(os.path.join(SITE, out_name), "w", encoding="utf-8") as fh:
        fh.write(str(soup))
    stats["pages"] += 1
    return True

# ---- build ----
if os.path.isdir(SITE): shutil.rmtree(SITE)
os.makedirs(SITE)
shutil.copytree(os.path.join(RAW, "mediawiki"), os.path.join(SITE, "mediawiki"))
if os.path.isdir(os.path.join(RAW, "misc")):
    shutil.copytree(os.path.join(RAW, "misc"), os.path.join(SITE, "misc"))
shutil.copy(os.path.join(SCRATCH, "overrides.css"), os.path.join(SITE, "overrides.css"))

for name, meta in filemap.items():
    if name not in write_names:      # loser of a case-collision; its file isn't emitted
        continue
    out = "index.html" if name == "Main_Page" else meta["file"]
    process(os.path.join(WIKI, meta["file"]), name, out)

# Cloudflare Pages redirects so the original MediaWiki URLs resolve
with open(os.path.join(SITE, "_redirects"), "w", encoding="utf-8") as fh:
    fh.write(REDIRECTS)

print("=== original-skin build stats ===")
for k in sorted(stats): print(f"  {stats[k]:5}  {k}")
print(f"\nSite written to {SITE}")
