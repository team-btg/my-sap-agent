# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose port (Cloud Run uses PORT env var, but 8080 is default)
EXPOSE 8080

# Command to run the application
# Using 0.0.0.0 is mandatory for Cloud Run
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
