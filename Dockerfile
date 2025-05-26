FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY api/requirements.txt .

# Uninstall potentially conflicting packages
RUN pip uninstall -y google-generativeai || true  # Old package name
RUN pip uninstall -y google-genai || true        # New package name, in case an old version is stuck

# Install requirements from the file
# This will install google-genai>=0.7.0 from our reqs
RUN pip install --no-cache-dir -r requirements.txt

# Install Aider
RUN pip install --upgrade aider-chat

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Create directory for application data
RUN mkdir -p /data/KinOS

# Expose the port (Render will set the PORT env var)
EXPOSE $PORT

# Run the API server
CMD python api/app.py
