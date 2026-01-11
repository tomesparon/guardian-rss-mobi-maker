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

# -----------------------------
FEEDS = {
    "UK News": "https://www.theguardian.com/uk-news/rss",
    "Technology": "https://www.theguardian.com/technology/rss",
    "World": "https://www.theguardian.com/world/rss",
    "Scotland": "https://www.theguardian.com/uk/scotland/rss",
}

ARTICLES_PER_FEED = 5
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

EPUB_FILE = OUTPUT / "guardian.epub"
MOBI_FILE = OUTPUT / "guardian.mobi"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# -----------------------------
book = epub.EpubBook()
book.set_identifier("guardian-daily")
book.set_title("Guardian Daily")
book.set_language("en")

# Cover
today = datetime.now().strftime("%A %d %B %Y")
cover = epub.EpubHtml(
    title="Cover",
    file_name="cover.xhtml",
    content=f"<h1>The Guardian Daily</h1><h3>{today}</h3><p>Generated edition</p>"
)
book.add_item(cover)

# Store chapters and TOC list
chapters_by_section = {}
all_chapters = []

img_counter = 1

# -----------------------------
print("Fetching RSS feeds...")

for section, url in FEEDS.items():
    print(f"\n== {section}")
    feed = feedparser.parse(url)
    section_list = []

    if not feed.entries:
        print(" ⚠ No entries found")
        chapters_by_section[section] = section_list
        continue

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

                    img_name = f"{section.lower()}-{idx}.jpg"
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

            fname = f"{section.lower()}-{idx}.xhtml"
            chap = epub.EpubHtml(
                title=entry.title,
                file_name=fname,
                content=str(soup)
            )
            book.add_item(chap)
            section_list.append((entry.title, fname))
            all_chapters.append(chap)

        except Exception as e:
            print("   article error:", e)

    chapters_by_section[section] = section_list

# -----------------------------
# NAVIGATION (manual nav.xhtml)
print("\nBuilding nav.xhtml...")

nav_html = ['<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Contents</title></head><body>']
nav_html.append("<h1>Table of Contents</h1>")

for section, items in chapters_by_section.items():
    nav_html.append(f"<h2>{section}</h2>")
    nav_html.append("<ul>")
    for title, fname in items:
        nav_html.append(f'<li><a href="{fname}">{title}</a></li>')
    nav_html.append("</ul>")

nav_html.append("</body></html>")

nav_page = epub.EpubHtml(title="Contents", file_name="nav.xhtml", content="".join(nav_html))
book.add_item(nav_page)

# -----------------------------
# Finalize EPUB
book.toc = [cover, nav_page] + all_chapters
book.spine = ["nav", cover, nav_page] + all_chapters

book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

CSS = """
body { font-family: serif; line-height:1.5; margin:1em; }
h1 { font-size:1.4em; }
h2 { font-size:1.2em; margin-top:1em; }
ul { margin-left: 1em; }
li { margin-bottom: 0.3em; }
"""
style = epub.EpubItem(uid="style", file_name="style/main.css", media_type="text/css", content=CSS)
book.add_item(style)

for chap in all_chapters + [cover, nav_page]:
    chap.add_item(style)

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
