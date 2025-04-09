FROM python:3.10-slim

WORKDIR /app

# Install git and other essential tools
RUN apt-get update && \
    apt-get install -y git curl wget gnupg2 apt-transport-https ca-certificates && \
    git --version && \
    git config --global --add safe.directory '*' && \
    # Make git available in standard locations
    ln -sf $(which git) /usr/local/bin/git && \
    # Ensure git is executable
    chmod +x $(which git) && \
    # Create symlinks to common locations
    mkdir -p /opt/render/bin && \
    ln -sf $(which git) /opt/render/bin/git

# Verify git installation
RUN which git && git --version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aider-chat

COPY . .

# Add a startup script that ensures git is available
RUN echo '#!/bin/bash\n\
echo "Checking git installation..."\n\
git --version || (apt-get update && apt-get install -y git)\n\
echo "Starting application..."\n\
python app.py' > /app/start.sh && \
chmod +x /app/start.sh

CMD ["/app/start.sh"]
