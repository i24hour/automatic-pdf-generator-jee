# Use custom base image with pre-installed LaTeX
FROM gcr.io/mentors-mantra-gen/mentors-mantra-base:latest

# Set working directory
WORKDIR /app

# Ensure logs are flushed immediately
ENV PYTHONUNBUFFERED=1

# (System dependencies are already installed in base image)

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
