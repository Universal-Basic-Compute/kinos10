FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY api/requirements.txt .

# Install specific version of Anthropic SDK first
RUN pip install --no-cache-dir anthropic==0.7.0

# Then install other requirements
RUN pip install --no-cache-dir -r requirements.txt

# Install Aider
RUN pip install aider-chat

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create directory for application data
RUN mkdir -p /data/KinOS

# Expose the API port
EXPOSE 5000

# Run the API server
CMD ["python", "api/app.py"]
