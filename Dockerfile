FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for WeasyPrint
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    zlib1g-dev \
    libpango-1.0-0 \
    libharfbuzz-subset0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Cargo
RUN  curl https://sh.rustup.rs -sSf | sh

ENV PATH="/root/.cargo/bin:${PATH}"
    
# Install WeasyPrint via pip
RUN pip cache purge && pip install weasyprint && pip install uv

COPY . .
ENV PATH="/app/bin:${PATH}"

RUN uv sync --frozen --no-cache
RUN uv pip install --system .

RUN mkdir -p deploy tmp

ENV PYTHONUNBUFFERED=1
ENV PROD=true

EXPOSE 5000

CMD ["uv", "run", "python", "main.py"]
