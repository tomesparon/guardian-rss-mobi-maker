FROM python:3.12-slim

WORKDIR /app

# Install dependencies including cron
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    pkg-config \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    cron \
    && rm -rf /var/lib/apt/lists/*

RUN pip uninstall -y lxml && \
    pip install --no-binary lxml lxml

# Install ebook-converter
RUN git clone https://github.com/gryf/ebook-converter /opt/ebook-converter
RUN cd /opt/ebook-converter && pip install .
RUN pip install PyQt5 humanize

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Setup Cron
COPY crontab /etc/cron.d/guardian-cron
RUN chmod 0644 /etc/cron.d/guardian-cron && \
    crontab /etc/cron.d/guardian-cron && \
    touch /var/log/cron.log

# Setup Entrypoint
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 5000
CMD ["/start.sh"]
