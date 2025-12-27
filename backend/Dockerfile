FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for LaTeX
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    texlive-pictures \
    texlive-science \
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
