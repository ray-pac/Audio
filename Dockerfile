FROM python:3.10-slim

# Install system dependencies (ffmpeg is required for audio manipulation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose Gradio's default port
EXPOSE 7860

# Configure Gradio to listen on all network interfaces
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"

# Command to run the application
CMD ["python", "app.py"]