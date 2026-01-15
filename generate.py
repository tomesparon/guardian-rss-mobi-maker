#!/usr/bin/env python3
import feedparser
import requests
from readability import Document
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from PIL import Image
import io
import subprocess
from datetime import datetime
import sys

# -----------------------------
FEEDS = {
    "UK News": "https://www.theguardian.com/uk-news/rss",
    "Technology": "https://www.theguardian.com/technology/rss",
    "World": "https://www.theguardian.com/world/rss",
    "Scotland": "https://www.theguardian.com/uk/scotland/rss",
    "Science": "https://www.theguardian.com/science/rss",
    "Business": "https://www.theguardian.com/business/rss",
    "Money": "https://www.theguardian.com/money/rss",
    "Film": "https://www.theguardian.com/film/rss",
    "TV and Radio": "https://www.theguardian.com/tv-and-radio/rss",
    "Games": "https://www.theguardian.com/games/rss",
}

ARTICLES_PER_FEED = 5
ENABLED_FEEDS = None

if len(sys.argv) > 1:
    try:
        ARTICLES_PER_FEED = int(sys.argv[1])
    except ValueError:
        pass  # Keep default if invalid

if len(sys.argv) > 2:
    # Second argument is comma-separated list of enabled feeds
    raw_feeds = sys.argv[2]
    if raw_feeds.strip():
        ENABLED_FEEDS = [f.strip() for f in raw_feeds.split(",") if f.strip()]

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

# Cleanup old files
print("Cleaning up old files...")
for old_file in OUTPUT.glob("*.epub"):
    old_file.unlink()
for old_file in OUTPUT.glob("*.mobi"):
    old_file.unlink()

today_str = datetime.now().strftime("%Y-%m-%d")
today_human = datetime.now().strftime("%d %B %Y")

EPUB_FILE = OUTPUT / f"guardian-{today_str}.epub"
MOBI_FILE = OUTPUT / f"guardian-{today_str}.mobi"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# -----------------------------
book = epub.EpubBook()
book.set_identifier(f"guardian-{today_str}")
book.set_title(f"Guardian Daily - {today_human}")
book.set_language("en")
book.add_author(today_human)

# Cover
cover = epub.EpubHtml(
    title="Cover",
    file_name="cover.xhtml",
    content=f"<h1>The Guardian Daily</h1><h3>{today_human}</h3><p>Generated edition</p>"
)
book.add_item(cover)

# Store structure for TOC: [(SectionName, [EpubHtml_objs...]), ...]
toc_structure = []
all_chapters = []

img_counter = 1

# -----------------------------
print("Fetching RSS feeds...")

for section_name, url in FEEDS.items():
    # Filter if enabled feeds are specified
    if ENABLED_FEEDS is not None and section_name not in ENABLED_FEEDS:
        continue

    print(f"\n== {section_name}")
    feed = feedparser.parse(url)
    
    if not feed.entries:
        print(" ⚠ No entries found")
        continue

    section_chapters = []

    for idx, entry in enumerate(feed.entries[:ARTICLES_PER_FEED], start=1):
        print(" •", entry.title)
        try:
            # Fetch article text
            r = requests.get(entry.link, headers=HEADERS, timeout=15)
            r.raise_for_status()

            soup = BeautifulSoup(Document(r.text).summary(), "html.parser")
            for svg in soup.find_all("svg"):
                svg.decompose()

            # Date
            pub_date = ""
            if hasattr(entry, "published_parsed"):
                d = datetime(*entry.published_parsed[:6])
                pub_date = d.strftime("%d %b %Y %H:%M")

            # Image
            if hasattr(entry, "media_content"):
                media = entry.media_content[-1]
                if len(entry.media_content) > 2:
                    media = entry.media_content[2]
                img_url = media.get("url")
            else:
                img_url = None

            if img_url:
                try:
                    img_res = requests.get(img_url, headers=HEADERS, timeout=10)
                    im = Image.open(io.BytesIO(img_res.content))
                    im = im.convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, "JPEG", quality=60)
                    img_data = buf.getvalue()

                    img_name = f"{section_name.lower().replace(' ', '')}-{idx}.jpg"
                    img_item = epub.EpubItem(
                        uid=img_name,
                        file_name=f"images/{img_name}",
                        media_type="image/jpeg",
                        content=img_data
                    )
                    book.add_item(img_item)

                    img_tag = soup.new_tag("img", src=f"images/{img_name}")
                    soup.insert(0, img_tag)
                except Exception as e:
                    print("   image failed:", e)

            # Build content
            h1 = soup.new_tag("h1")
            h1.string = entry.title
            soup.insert(0, h1)

            if pub_date:
                p_date = soup.new_tag("p")
                p_date.string = pub_date
                soup.insert(1, p_date)

            fname = f"{section_name.lower().replace(' ', '')}-{idx}.xhtml"
            chap = epub.EpubHtml(
                title=entry.title,
                file_name=fname,
                content=str(soup)
            )
            book.add_item(chap)
            
            section_chapters.append(chap)
            all_chapters.append(chap)

        except Exception as e:
            print("   article error:", e)

    if section_chapters:
        toc_structure.append((section_name, section_chapters))

# -----------------------------
# BBC INTEGRATION
# -----------------------------
if ENABLED_FEEDS is None or "BBC Top Stories" in ENABLED_FEEDS:
    try:
        from bbc_fetcher import fetch_bbc_news
        bbc_items = fetch_bbc_news(ARTICLES_PER_FEED, book)
        if bbc_items:
            toc_structure.append(("BBC Top Stories", bbc_items))
            all_chapters.extend(bbc_items)
    except Exception as e:
        print(f"⚠ Failed to fetch BBC: {e}")

# -----------------------------
# HACKER NEWS INTEGRATION
# -----------------------------
if ENABLED_FEEDS is None or "Hacker News (Comments)" in ENABLED_FEEDS:
    try:
        from hn_fetcher import fetch_hn_threads
        hn_items = fetch_hn_threads(ARTICLES_PER_FEED, book)
        if hn_items:
            toc_structure.append(("Hacker News", hn_items))
            all_chapters.extend(hn_items)
    except Exception as e:
        print(f"⚠ Failed to fetch Hacker News: {e}")

# -----------------------------
# NAVIGATION (manual nav.xhtml)
print("\nBuilding nav.xhtml...")

nav_html = ['<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Contents</title></head><body>']
nav_html.append("<h1>Table of Contents</h1>")

for section_name, chapters in toc_structure:
    nav_html.append(f"<h2>{section_name}</h2>")
    nav_html.append("<ul>")
    for chap in chapters:
        nav_html.append(f'<li><a href="{chap.file_name}">{chap.title}</a></li>')
    nav_html.append("</ul>")

nav_html.append("</body></html>")

nav_page = epub.EpubHtml(title="Contents", file_name="nav.xhtml", content="".join(nav_html))
book.add_item(nav_page)

# -----------------------------
# Finalize EPUB
# Construct hierarchical TOC for device menu
device_toc = [cover, nav_page]
for section_name, chapters in toc_structure:
    device_toc.append(
        (epub.Section(section_name), chapters)
    )

book.toc = device_toc
book.spine = ["nav", cover, nav_page] + all_chapters

book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

CSS = """
body { font-family: serif; line-height:1.5; margin:1em; }
h1 { font-size:1.4em; }
h2 { font-size:1.2em; margin-top:1em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }
ul { margin-left: 1em; padding-left: 0; list-style-type: none; }
li { margin-bottom: 0.5em; }
a { text-decoration: none; color: #000; }
a:hover { text-decoration: underline; }
img { max-width: 100%; height: auto; display: block; margin: 1em 0; }
"""
style = epub.EpubItem(uid="style", file_name="style/main.css", media_type="text/css", content=CSS)
book.add_item(style)

for chap in all_chapters + [cover, nav_page]:
    chap.add_item(style)

# -----------------------------
# Update Cover with Top Story
# -----------------------------
top_headline = "Daily Edition"
if all_chapters:
    # Get the title of the first article
    top_headline = all_chapters[0].title

# Newspaper Style Cover HTML
cover_html = f"""
    <div style="text-align: center; font-family: 'Times New Roman', serif; margin-top: 2em;">
        <h1 style="font-size: 3em; line-height: 1; border-bottom: 3px double black; padding-bottom: 0.5em; margin-bottom: 0.2em;">The Guardian Daily</h1>
        <p style="border-bottom: 1px solid #666; padding-bottom: 0.5em; margin-top: 0; font-style: italic; font-size: 1.1em; color: #333;">
            {today_human} &bull; Generated Edition
        </p>
        
        <div style="margin-top: 4em; padding: 0 1em;">
            <p style="text-transform: uppercase; font-size: 0.9em; letter-spacing: 2px; color: #555; margin-bottom: 0.5em;">Top Story</p>
            <h2 style="font-size: 2.5em; line-height: 1.2; font-weight: bold; margin-top: 0;">{top_headline}</h2>
        </div>
        
        <div style="margin-top: 5em; font-size: 0.9em; color: #888;">
            <p>Plus {len(all_chapters)-1 if len(all_chapters) > 1 else 0} other stories</p>
        </div>
    </div>
"""

cover.content = cover_html

# -----------------------------
print("Writing EPUB...")
epub.write_epub(EPUB_FILE, book)

print("Converting MOBI...")
try:
    subprocess.check_call(["ebook-converter", str(EPUB_FILE), str(MOBI_FILE)])
    print("✔ MOBI created")
except subprocess.CalledProcessError:
    print("⚠ MOBI failed")

print(f"\nDone — EPUB: {EPUB_FILE}, MOBI: {MOBI_FILE}")
