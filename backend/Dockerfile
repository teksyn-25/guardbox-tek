FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libvips-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --system --no-create-home --shell /usr/sbin/nologin guardbox \
    && mkdir -p /data/guardbox \
    && chown guardbox:guardbox /data/guardbox
USER guardbox

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
