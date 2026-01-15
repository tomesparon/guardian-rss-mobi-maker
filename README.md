# News-to-eBook Generator

A self-hosted tool that aggregates news from various sources (The Guardian, BBC, Hacker News) and compiles them into a  readable eBook (EPUB & MOBI) delivered via a web interface or sent directly to your Kindle.

## Features

- **Multi-Source Aggregation**: Fetches articles from:
  - The Guardian (UK, Tech, World, Science, Business, etc.)
  - BBC Top Stories
  - Hacker News (including comment threads)
- **Web Interface**: Simple Flask-based UI to trigger generations and download the latest editions.
- **Customizable**: Choose how many articles to fetch per section.
- **Automated Scheduling**: Automatically attempts to generate a new edition daily at 9:00 AM.
- **Format Support**: Generates both **EPUB** (generic e-readers) and **MOBI** (Kindle) using `ebook-converter` - https://github.com/gryf/ebook-converter
- **Send to Kindle**: Built-in email service to push the generated MOBI file directly to your Kindle device.
- **Clean Layout**: Uses `readability` and `BeautifulSoup` to strip clutter and format articles for e-ink displays.

## Quick Start (Docker)

The easiest way to run the application is using Docker, as it handles all dependencies including the `ebook-converter` tool.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/gptbooks.git
   cd gptbooks
   ```

2. **Configure Environment:**
   Create a `.env` file (optional, mostly for email settings):
   ```env
   # Optional: For Send-to-Kindle functionality
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   KINDLE_EMAIL=your-kindle@kindle.com
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Access the App:**
   Open your browser and navigate to `http://localhost:5000`.

## Manual Installation

If you prefer to run it without Docker, you will need Python 3 and the `ebook-converter` tool by [gryf](https://github.com/gryf/ebook-converter) installed on your system.

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ebook-converter:**
   ```bash
   pip install git+https://github.com/gryf/ebook-converter.git
   ```

3. **Run the Application:**
   ```bash
   python app.py
   ```

## Usage

### Web Interface
- **Generate**: Enter the number of articles you want per section (default: 5) and click "Generate New Edition".
- **Download**: Links for EPUB and MOBI files will appear once generation is complete.
- **Send to Kindle**: If configured, enter your Kindle email (or use the default from `.env`) to wirelessly deliver the book.

### CLI Usage
You can also run the generator directly via the command line:

```bash
# Generate with default settings (5 articles per section)
python generate.py

# Generate with custom article count
python generate.py 10

# Generate specific sections only
python generate.py 5 "Technology, World, Hacker News"
```

## Project Structure

- `app.py`: Flask web application and internal scheduler.
- `generate.py`: Core logic for fetching feeds and building the eBook.
- `bbc_fetcher.py` / `hn_fetcher.py`: Specialized modules for specific sources.
- `templates/index.html`: Web interface template.
- `output/`: Directory where generated files are stored.

## License

MIT / YOLO