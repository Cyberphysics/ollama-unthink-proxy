#!/bin/bash
# 测试完整响应（非流式）

# 检查jq是否安装
if ! command -v jq &> /dev/null; then
    echo "需要安装jq工具，请运行: apt-get install -y jq"
    exit 1
fi

# 获取可用模型
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

# 测试原始Ollama服务的完整响应
echo -e "\n测试原始Ollama服务的完整响应..."
curl -X POST http://10.252.17.12:11434/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"请简要介绍Python语言的主要特点，不超过100字。\"}],\"stream\":false}" | jq .

# 测试代理服务的完整响应
echo -e "\n测试代理服务的完整响应..."
curl -X POST http://localhost:11435/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"请简要介绍Python语言的主要特点，不超过100字。\"}],\"stream\":false}" | jq .