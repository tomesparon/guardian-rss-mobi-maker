FROM python:3.12-slim

WORKDIR /app

# REQUIRED build deps for html5-parser
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    pkg-config \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip uninstall -y lxml && \
    pip install --no-binary lxml lxml

# Install ebook-converter
RUN git clone https://github.com/gryf/ebook-converter /opt/ebook-converter
RUN cd /opt/ebook-converter && pip install .
RUN pip install PyQt5 humanize
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python3", "app.py"]