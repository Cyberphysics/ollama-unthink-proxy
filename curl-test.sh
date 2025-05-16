#!/bin/bash
# 测试Unthink Proxy API

echo "测试Unthink Proxy API..."
curl -X POST http://localhost:11435/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3","messages":[{"role":"user","content":"Hello, world!"}]}'

echo -e "\n\n测试原始Ollama API..."
curl -X POST http://10.252.17.12:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3","messages":[{"role":"user","content":"Hello, world!"}]}'