# KinOS Setup Instructions

## Setting Up a Virtual Environment

To avoid dependency conflicts with other Python packages, it's recommended to use a virtual environment:

### Windows

```bash
# Create a virtual environment
python -m venv kinos-env

# Activate the virtual environment
kinos-env\Scripts\activate

# Install requirements
cd api
pip install -r requirements.txt

# Run the API
python app.py
```

### macOS/Linux

```bash
# Create a virtual environment
python -m venv kinos-env

# Activate the virtual environment
source kinos-env/bin/activate

# Install requirements
cd api
pip install -r requirements.txt

# Run the API
python app.py
```

## Environment Variables

Create a `.env` file in the root directory with your Anthropic API key:

```
ANTHROPIC_API_KEY=your_api_key_here
```

## Running the Web UI

In a separate terminal (with the virtual environment activated):

```bash
cd website
python app.py
```

Access the web UI at `http://localhost:5000`

## Troubleshooting

If you encounter dependency conflicts even with a virtual environment, you can try:

```bash
pip install httpcore==0.17.3 httpx==0.24.1
```

This should resolve most conflicts with packages like aider-chat and open-interpreter.
