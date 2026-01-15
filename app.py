#!/usr/bin/env python3
from flask import Flask, send_file, render_template, redirect, url_for, request, jsonify
from pathlib import Path
from ebooklib import epub
from bs4 import BeautifulSoup
import humanize  # pip install humanize
import threading
import time
import subprocess
import sys
from datetime import datetime, timedelta

# -----------------------------
# Configuration
# -----------------------------
app = Flask(__name__)
OUTPUT = Path("output")
GENERATION_STATE = {"status": "idle", "message": ""}

# -----------------------------
# Scheduler & Generation Logic
# -----------------------------
def run_generation_process(article_count, sections_arg):
    global GENERATION_STATE
    GENERATION_STATE = {"status": "running", "message": "Starting generation..."}
    
    try:
        # Run the script
        subprocess.check_call([sys.executable, "generate.py", article_count, sections_arg])
        GENERATION_STATE = {"status": "complete", "message": "Generation successful!"}
    except subprocess.CalledProcessError as e:
        GENERATION_STATE = {"status": "error", "message": f"Error: {e}"}
    except Exception as e:
        GENERATION_STATE = {"status": "error", "message": f"Unexpected error: {e}"}
    
    # Wait a bit then reset
    time.sleep(5)
    if GENERATION_STATE["status"] == "complete":
        GENERATION_STATE = {"status": "idle", "message": ""}

def run_generation_task():
    # Helper for the scheduled task
    global GENERATION_STATE
    if GENERATION_STATE["status"] == "running":
        print("Skipping scheduled run: Generation already in progress.")
        return

    print(f"[{datetime.now()}] Starting scheduled generation...")
    # Default: 5 articles, all sections
    run_generation_process("5", "")

def scheduler_loop():
    while True:
        now = datetime.now()
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        if now >= target:
            target = target + timedelta(days=1)
            
        wait_seconds = (target - now).total_seconds()
        print(f"[{now}] Scheduler: Next run in {wait_seconds/3600:.2f} hours ({target})")
        
        time.sleep(wait_seconds)
        run_generation_task()
        time.sleep(60) 

def start_scheduler():
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()

# Start scheduler on launch
start_scheduler()

# -----------------------------
# Helpers
# -----------------------------
def get_latest_file(extension: str) -> Path:
    files = list(OUTPUT.glob(f"*.{extension}"))
    if not files:
        return None
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0]

def human_readable_size(file_path: Path) -> str:
    if file_path and file_path.exists():
        return humanize.naturalsize(file_path.stat().st_size)
    return "0 B"

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET"])
def index():
    titles = []
    epub_file = get_latest_file("epub")
    mobi_file = get_latest_file("mobi")

    if epub_file and epub_file.exists():
        try:
            book = epub.read_epub(str(epub_file))
            for item in book.items:
                if isinstance(item, epub.EpubHtml):
                    title = item.title
                    if not title:
                        soup = BeautifulSoup(item.content, "html.parser")
                        h1 = soup.find("h1")
                        title = h1.get_text() if h1 else item.file_name
                    if title and title not in ["Table of Contents", "Cover", "Contents"]:
                        titles.append(title)
        except Exception as e:
            print(f"Error reading epub: {e}")

    return render_template(
        "index.html",
        titles=titles,
        epub_exists=epub_file is not None,
        mobi_exists=mobi_file is not None,
        epub_size=human_readable_size(epub_file),
        mobi_size=human_readable_size(mobi_file)
    )

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(GENERATION_STATE)

@app.route("/generate", methods=["POST"])
def gen():
    global GENERATION_STATE
    if GENERATION_STATE["status"] == "running":
        return redirect(url_for("index"))

    article_count = request.form.get("article_count", "5")
    selected_sections = request.form.getlist("sections")
    sections_arg = ",".join(selected_sections) if selected_sections else ""

    thread = threading.Thread(target=run_generation_process, args=(article_count, sections_arg))
    thread.start()
    
    return redirect(url_for("index"))

@app.route("/download/<fmt>", methods=["GET"])
def download(fmt):
    target_file = get_latest_file(fmt)
    if target_file and target_file.exists():
        return send_file(str(target_file), as_attachment=True)
    return redirect(url_for("index"))

@app.route("/send-kindle", methods=["POST"])
def send_kindle_route():
    from email_service import send_to_kindle
    custom_email = request.form.get("custom_email")
    if custom_email and not custom_email.strip():
        custom_email = None
        
    epub_file = get_latest_file("epub")
    if epub_file:
        success = send_to_kindle(epub_file, override_email=custom_email)
        if success:
            print(f"Sent EPUB to Kindle ({custom_email if custom_email else 'default'}) via web request.")
    return redirect(url_for("index"))

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
