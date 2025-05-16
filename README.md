# Ollama Unthink Proxy

## Description

A production-ready Ollama proxy that removes Chain-of-Thought process from
raw LLM output. This proxy filters out content between configurable thinking tags
in LLM responses, providing clean output for applications.

## Features

- Configurable `OPEN_THINK_TAG` and `CLOSE_THINK_TAG`
- Production-ready with Gunicorn/Waitress WSGI server
- Comprehensive error handling and logging
- Health check endpoint for monitoring
- Prometheus metrics integration
- Docker runtime with security best practices
- Monitoring dashboard with Grafana
- Automated testing with pytest

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| OLLAMA_SERVER | URL of the Ollama server | http://ollama:11434 |
| PROXY_PORT | Port for the proxy server | 11434 |
| OPEN_THINK_TAG | Tag that marks the beginning of thinking content | <think> |
| CLOSE_THINK_TAG | Tag that marks the end of thinking content | </think> |
| LOG_LEVEL | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| LOG_DIR | Directory for log files | logs |
| REQUEST_TIMEOUT | Timeout for requests to Ollama (seconds) | 60 |
| MAX_RETRIES | Maximum number of retry attempts | 3 |
| RETRY_DELAY | Delay between retry attempts (seconds) | 1 |
| DEBUG_MODE | Enable debug mode | false |

## Setup with Local Ollama Server

This setup uses an existing Ollama server running on the host machine.

### Prerequisites

1. Ensure Ollama is installed and running on your host machine
2. Make sure Ollama is listening on all interfaces:
   ```bash
   # Add to ~/.ollama/.env
   OLLAMA_HOST=0.0.0.0
   ```
3. Restart Ollama service

### Quick Start

```bash
# Make the startup script executable
chmod +x start-local.sh

# Start the services
./start-local.sh
```

This will start:
- Unthink proxy (connecting to host Ollama service)
- Prometheus for metrics collection
- Grafana for monitoring dashboards

Access the services:
- Proxy: http://localhost:11435
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### Manual Setup

1. Edit `docker-compose.yml` to point to your Ollama server
2. Start the services:
   ```bash
   docker compose up -d
   ```

## API Endpoints

- `/api/generate`, `/api/chat`, `/api/show`: Proxied Ollama API endpoints
- `/health`: Health check endpoint
- `/metrics`: Prometheus metrics endpoint

## Testing

```bash
pytest --cov=.
```

## Acknowledgments

- https://github.com/vhanla/deepseek-r1-unthink for the initial version
- Ollama team for the LLM engine
- Flask for the web framework