#!/bin/bash
# 测试Unthink Proxy API

# 首先检查可用模型
echo "检查可用模型..."
MODELS=$(curl -s http://10.252.17.12:11434/api/tags | jq -r '.models[].name' 2>/dev/null)

if [ -z "$MODELS" ]; then
  echo "没有找到可用模型，请先拉取一个模型"
  echo "例如: ollama pull llama2"
  exit 1
fi

# 使用第一个可用模型
MODEL=$(echo "$MODELS" | head -n 1)
echo "使用模型: $MODEL"

echo -e "\n测试Unthink Proxy API..."
curl -X POST http://localhost:11435/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello, world!\"}]}"

echo -e "\n\n测试原始Ollama API..."
curl -X POST http://10.252.17.12:11434/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello, world!\"}]}"