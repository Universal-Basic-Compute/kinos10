FROM python:3.10-slim

WORKDIR /app

# Install git first, then Python dependencies
RUN apt-get update && \
    apt-get install -y git && \
    git --version && \
    git config --global --add safe.directory '*'

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aider-chat

COPY . .

CMD ["python", "app.py"]
