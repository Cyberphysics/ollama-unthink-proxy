#!/bin/bash
# 设置Ollama服务和拉取模型

# 检查Ollama是否已安装
if ! command -v ollama &> /dev/null; then
    echo "Ollama未安装，正在安装..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "Ollama安装完成"
else
    echo "Ollama已安装"
fi

# 确保Ollama服务正在运行
if ! pgrep -x "ollama" > /dev/null; then
    echo "启动Ollama服务..."
    ollama serve &
    sleep 5
else
    echo "Ollama服务已在运行"
fi

# 检查是否有可用模型
MODELS=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null)

if [ -z "$MODELS" ]; then
    echo "没有找到可用模型，正在拉取llama2模型..."
    ollama pull llama2
    echo "模型拉取完成"
else
    echo "已有可用模型:"
    echo "$MODELS"
fi

# 确保Ollama监听在所有接口
OLLAMA_ENV_FILE="$HOME/.ollama/.env"
if [ ! -f "$OLLAMA_ENV_FILE" ] || ! grep -q "OLLAMA_HOST=0.0.0.0" "$OLLAMA_ENV_FILE"; then
    echo "配置Ollama监听在所有接口..."
    mkdir -p "$HOME/.ollama"
    echo "OLLAMA_HOST=0.0.0.0" >> "$OLLAMA_ENV_FILE"
    
    # 重启Ollama服务
    pkill ollama
    sleep 2
    ollama serve &
    sleep 5
    echo "Ollama服务已重启并监听在所有接口"
fi

echo "Ollama设置完成，可以使用以下命令测试:"
echo "./curl-test.sh"