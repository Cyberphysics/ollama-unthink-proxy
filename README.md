# Ollama Unthink Proxy

## Description

Very simple Ollama proxy that used to remove Chain-of-Thought process from
raw LLM output. This repository is a temporary workaround until the community
will find a better way to handle `think` tokens.

Intended usage - LLM debug and development. Works rather well with Zed IDE.

**Important**: NOT recommended for `PRODUCTION` as the code was written without
performance optimization in mind.

## Features

- Configurable `OPEN_THINK_TAG` and `CLOSE_THINK_TAG`;
- Monitoring RAW LLM prompt;
- Monitoring RAW LLM output;
- Docker runtime;
- Ollama included;

## Setup

### Docker (with ollama and Nvidia GPU)

```
docker compose up
```

### pip (standalone)

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python3 unthink-proxy.py
```

## Acknowledgments

- https://github.com/vhanla/deepseek-r1-unthink for the initial version;
- Ollama team for the LLM engine;
- Flask for the easy-to-use App server;
