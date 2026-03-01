# Use custom base image with pre-installed LaTeX
FROM gcr.io/mentors-mantra-gen/mentors-mantra-base:latest

# Set working directory
WORKDIR /app

# Ensure logs are flushed immediately
ENV PYTHONUNBUFFERED=1

# Install build tools and system deps needed to compile pycairo & manimpango (Manim deps)
# This is needed until the base image is rebuilt with these tools included
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    meson \
    ninja-build \
    pkg-config \
    python3-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-xlib-2.0-dev \
    ffmpeg \
    dvisvgm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p output

# Expose port
EXPOSE 8000

# Run the application with dynamic port for Heroku
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
