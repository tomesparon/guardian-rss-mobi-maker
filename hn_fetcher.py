import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from datetime import datetime
import time

# Official HN API
API_BASE = "https://hacker-news.firebaseio.com/v0"
HEADERS = {"User-Agent": "GuardianEbookGenerator/1.0"}

def fetch_item(item_id):
    """
    Fetches a single item (story or comment) from the HN API.
    """
    try:
        r = requests.get(f"{API_BASE}/item/{item_id}.json", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"   Error fetching item {item_id}: {e}")
    return None

def build_comment_html(comment_id, depth=0):
    """
    Recursively fetches and builds HTML for a comment tree.
    Limiting depth and count to avoid thousands of requests.
    """
    if depth > 3: # Limit nesting depth
        return ""
        
    comment = fetch_item(comment_id)
    if not comment or comment.get("deleted") or comment.get("dead"):
        return ""
        
    text = comment.get("text", "")
    if not text:
        return ""
        
    user = comment.get("by", "anon")
    
    # Visual indentation
    margin_left = depth * 1.5
    top_style = "border-top: 1px solid #eee; padding-top: 10px; margin-top: 10px;" if depth == 0 else ""
    
    html = f"""
    <div style="margin-left: {margin_left}em; {top_style} margin-bottom: 10px; font-family: sans-serif;">
        <div style="font-size: 0.85em; color: #555; margin-bottom: 4px;">
            <strong>{user}</strong>
        </div>
        <div style="line-height: 1.4;">
            {text}
        </div>
    </div>
    """
    
    # We are no longer fetching replies (kids) as per user request
    return html

def fetch_hn_threads(limit, book):
    """
    Fetches top HN threads and their comments using the API.
    """
    print(f"\n== Hacker News (API)")
    
    # 1. Get Top Stories
    try:
        r = requests.get(f"{API_BASE}/topstories.json", headers=HEADERS, timeout=10)
        r.raise_for_status()
        top_ids = r.json()
    except Exception as e:
        print(f" ⚠ Failed to fetch top stories: {e}")
        return []

    chapters = []
    count = 0

    # 2. Process each story
    for story_id in top_ids:
        if count >= limit:
            break
            
        story = fetch_item(story_id)
        if not story:
            continue
            
        title = story.get("title", "No Title")
        print(f" • {title}")
        
        # Build Chapter Content
        soup = BeautifulSoup("<div></div>", "html.parser")
        
        # Header
        h1 = soup.new_tag("h1")
        h1.string = title
        soup.append(h1)
        
        # Links
        if "url" in story:
            p_link = soup.new_tag("p")
            link_a = soup.new_tag("a", href=story["url"])
            link_a.string = "Read Article / Context"
            p_link.append(link_a)
            soup.append(p_link)
            
        p_thread = soup.new_tag("p")
        hn_url = f"https://news.ycombinator.com/item?id={story_id}"
        thread_a = soup.new_tag("a", href=hn_url)
        thread_a.string = "Original HN Thread"
        p_thread.append(thread_a)
        soup.append(p_thread)
        
        hr = soup.new_tag("hr")
        soup.append(hr)
        
        h2 = soup.new_tag("h2")
        h2.string = "Discussion"
        soup.append(h2)
        
        # Fetch Top Comments (Kids)
        # Reduced limit to 50 comments total per story for better speed
        MAX_COMMENTS_PER_STORY = 50
        kids = story.get("kids", [])
        
        if not kids:
            p_no = soup.new_tag("p")
            p_no.string = "No comments yet."
            soup.append(p_no)
        else:
            print(f"   Fetching up to {MAX_COMMENTS_PER_STORY} comments for {story_id}...")
            comments_html = ""
            comments_fetched = 0
            
            # Use a queue-based approach for breadth-first or just a controlled recursive one
            # To keep it simple, we'll iterate root kids and let them recurse a bit
            for kid_id in kids:
                if comments_fetched >= MAX_COMMENTS_PER_STORY:
                    break
                
                # We'll allow each root comment to fetch its subtree, 
                # but we'll stop the whole process once we hit 100 total.
                comment_tree_html = build_comment_html(kid_id, depth=0)
                if comment_tree_html:
                    comments_html += comment_tree_html
                    # Rough count of comments added (estimated by looking for the user-header div)
                    comments_fetched += comment_tree_html.count('<strong>')
            
            # Append comments
            c_soup = BeautifulSoup(comments_html, "html.parser")
            soup.append(c_soup)

        # Create Chapter
        fname = f"hn-{count}.xhtml"
        chap = epub.EpubHtml(
            title=f"HN: {title}",
            file_name=fname,
            content=str(soup)
        )
        book.add_item(chap)
        chapters.append(chap)
        count += 1
        
    return chapters