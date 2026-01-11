#!/usr/bin/env python3
from flask import Flask, send_file, render_template_string, redirect, url_for
from pathlib import Path
from ebooklib import epub
from bs4 import BeautifulSoup
import humanize  # pip install humanize

# -----------------------------
# Configuration
# -----------------------------
app = Flask(__name__)
OUTPUT = Path("output")
EPUB_FILE = OUTPUT / "guardian.epub"
MOBI_FILE = OUTPUT / "guardian.mobi"

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Guardian eBook</title>
<style>
body { font-family: Georgia, serif; margin: 1em; }
h1 { font-size: 1.8em; }
h2 { font-size: 1.4em; margin-top: 2em; }
ul { list-style: none; padding-left: 0; }
li { margin-bottom: 0.5em; }
a.button {
    display: inline-block;
    padding: 0.5em 1em;
    margin: 0.5em 0;
    text-decoration: none;
    background: #007acc;
    color: white;
    border-radius: 4px;
}
a.button:hover { background: #005fa3; }
hr { margin: 2em 0; }
</style>
</head>
<body>
<h1>Guardian eBook</h1>

<form method="post" action="/generate">
<button type="submit" class="button">Generate / Refresh eBook</button>
</form>

{% if chapters %}
<hr>
<h2>Articles</h2>
<ul>
{% for chap in chapters %}
<li>{{ chap.title }}</li>
{% endfor %}
</ul>

<hr>
<h2>Download</h2>
<ul>
{% if epub_file.exists() %}
<li>
<a href="/download/epub" class="button">Download EPUB ({{ epub_size }})</a>
</li>
{% endif %}
{% if mobi_file.exists() %}
<li>
<a href="/download/mobi" class="button">Download MOBI ({{ mobi_size }})</a>
</li>
{% endif %}
</ul>
{% endif %}
</body>
</html>
"""

# -----------------------------
# Helpers
# -----------------------------
def human_readable_size(file_path: Path) -> str:
    if file_path.exists():
        return humanize.naturalsize(file_path.stat().st_size)
    return "0 B"

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET"])
def index():
    chapters = []
    if EPUB_FILE.exists():
        book = epub.read_epub(str(EPUB_FILE))
        for item in book.items:
            if isinstance(item, epub.EpubHtml):
                # Get chapter title: first try item.title
                title = item.title
                if not title:
                    # fallback: parse first <h1>
                    soup = BeautifulSoup(item.content, "html.parser")
                    h1 = soup.find("h1")
                    title = h1.get_text() if h1 else item.file_name
                chapters.append({"title": title, "file_name": item.file_name})

    return render_template_string(
        HTML_TEMPLATE,
        chapters=chapters,
        epub_file=EPUB_FILE,
        mobi_file=MOBI_FILE,
        epub_size=human_readable_size(EPUB_FILE),
        mobi_size=human_readable_size(MOBI_FILE)
    )

@app.route("/download/<fmt>", methods=["GET"])
def download(fmt):
    if fmt == "epub" and EPUB_FILE.exists():
        return send_file(str(EPUB_FILE), as_attachment=True)
    elif fmt == "mobi" and MOBI_FILE.exists():
        return send_file(str(MOBI_FILE), as_attachment=True)
    return redirect(url_for("index"))

@app.route("/generate", methods=["POST"])
def gen():
    # This just calls generate.py
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "generate.py"])
    except subprocess.CalledProcessError as e:
        print(f"Error generating eBook: {e}")
    return redirect(url_for("index"))

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    app.run(host="0.0.0.0", port=5000)