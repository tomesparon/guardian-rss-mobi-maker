import feedparser
import requests
from readability import Document
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image
import io
from datetime import datetime

BBC_FEED_URL = "http://feeds.bbci.co.uk/news/rss.xml"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_bbc_news(limit, book):
    """
    Fetches top stories from BBC News, cleans them, and returns a list of EpubHtml objects.
    """
    print(f"\n== BBC Top Stories")
    feed = feedparser.parse(BBC_FEED_URL)
    
    if not feed.entries:
        print(" ⚠ No entries found")
        return []

    chapters = []
    count = 0

    for idx, entry in enumerate(feed.entries):
        if count >= limit:
            break

        # 1. Filter out non-article content
        # BBC Live blogs often contain '/live/'
        # BBC Video pages often contain '/av/'
        if "/live/" in entry.link or "/av/" in entry.link:
            continue

        print(" •", entry.title)
        
        try:
            # 2. Fetch content
            r = requests.get(entry.link, headers=HEADERS, timeout=15)
            r.raise_for_status()

            # 3. Parse with Readability
            doc = Document(r.text)
            soup = BeautifulSoup(doc.summary(), "html.parser")

            # 4. BBC Specific Cleanup
            # Remove "Related Topics" or "More on this story" often found in footer divs
            for div in soup.find_all("div", attrs={"data-component": "text-block"}):
                 if div.get_text().strip() == "Related Topics":
                     div.decompose()

            # Remove video placeholders if they remain
            for fig in soup.find_all("figure", class_="media-player"):
                fig.decompose()

            # 5. Image Handling
            # Try to find a high-res image from the metadata or the entry
            img_url = None
            if hasattr(entry, "media_thumbnail"):
                # BBC RSS often has media_thumbnail
                thumbnails = entry.media_thumbnail
                if thumbnails:
                    # Pick the largest if multiple (usually the last one is biggest)
                    img_url = thumbnails[-1]['url']
            
            if img_url:
                try:
                    # Basic image download and processing
                    img_res = requests.get(img_url, headers=HEADERS, timeout=10)
                    im = Image.open(io.BytesIO(img_res.content))
                    im = im.convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, "JPEG", quality=60)
                    img_data = buf.getvalue()

                    # Unique ID for the image
                    img_name = f"bbc-{count}.jpg"
                    img_item = epub.EpubItem(
                        uid=img_name,
                        file_name=f"images/{img_name}",
                        media_type="image/jpeg",
                        content=img_data
                    )
                    book.add_item(img_item)

                    # Insert into soup
                    img_tag = soup.new_tag("img", src=f"images/{img_name}")
                    soup.insert(0, img_tag)
                except Exception as e:
                    print(f"   image failed: {e}")

            # 6. Build Content
            h1 = soup.new_tag("h1")
            h1.string = entry.title
            soup.insert(0, h1)

            # Add Date
            if hasattr(entry, "published_parsed"):
                d = datetime(*entry.published_parsed[:6])
                p_date = soup.new_tag("p")
                p_date.string = d.strftime("%d %b %Y %H:%M")
                soup.insert(1, p_date)

            # Create Chapter
            fname = f"bbc-{count}.xhtml"
            chap = epub.EpubHtml(
                title=entry.title,
                file_name=fname,
                content=str(soup)
            )
            book.add_item(chap)
            chapters.append(chap)
            count += 1

        except Exception as e:
            print(f"   article error: {e}")

    return chapters
