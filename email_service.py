import smtplib
import os
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_to_kindle(file_path: Path, override_email: str = None):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    # Use override if provided, otherwise env var
    kindle_email = override_email if override_email else os.getenv("KINDLE_EMAIL")

    if not all([smtp_server, smtp_port, smtp_user, smtp_password, kindle_email]):
        print("⚠ Email configuration missing (check .env or provide email). Skipping Send to Kindle.")
        return False

    if not file_path.exists():
        print(f"⚠ File {file_path} does not exist. Cannot send.")
        return False

    print(f"📧 Sending {file_path.name} to {kindle_email}...")

    msg = EmailMessage()
    msg['Subject'] = "Convert"  # "Convert" subject helps Amazon convert PDF/HTML if needed, though we send MOBI/EPUB
    msg['From'] = smtp_user
    msg['To'] = kindle_email
    msg.set_content("Here is your daily Guardian digest.")

    # Read and attach file
    with open(file_path, 'rb') as f:
        file_data = f.read()
        msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_path.name)

    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as s:
            s.starttls()
            s.login(smtp_user, smtp_password)
            s.send_message(msg)
        print("✔ Email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

if __name__ == "__main__":
    # Test run
    import sys
    if len(sys.argv) > 1:
        send_to_kindle(Path(sys.argv[1]))
    else:
        print("Usage: python email_service.py <path_to_file>")
