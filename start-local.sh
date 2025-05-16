#!/bin/bash
# 使用本地Ollama服务启动Unthink Proxy

# 检查本地Ollama服务是否可访问
echo "检查本地Ollama服务..."
if curl -s http://10.252.17.12:11434/api/tags > /dev/null; then
    echo "✅ 本地Ollama服务可访问"
else
    echo "❌ 无法连接到本地Ollama服务，请确保服务已启动并监听在10.252.17.12:11434"
    exit 1
fi

# 启动代理服务
echo "启动Unthink Proxy服务..."
docker compose up -d

echo "服务已启动:"
echo "- Unthink Proxy: http://localhost:11435"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000"

echo -e "\n测试代理服务:"
echo "curl -X POST http://localhost:11435/api/chat -d '{\"model\":\"llama3\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello, world!\"}]}'"