#!/bin/bash
# 检查Ollama服务和可用模型

echo "检查Ollama服务状态..."
curl -s http://10.252.17.12:11434/api/tags | jq .

echo -e "\n可用模型列表:"
curl -s http://10.252.17.12:11434/api/tags | jq '.models[].name'

echo -e "\n如果上面没有显示模型列表，请拉取一个模型:"
echo "ollama pull llama3"
echo "或"
echo "ollama pull llama2"