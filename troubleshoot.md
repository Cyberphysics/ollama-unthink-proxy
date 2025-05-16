# Ollama Unthink Proxy 故障排除指南

## 常见问题

### 1. 无法连接到Ollama服务

错误信息: `404 Client Error: Not Found for url: http://10.252.17.12:11434/api/chat`

可能原因:
- Ollama服务未运行
- Ollama服务未监听在指定IP上
- 防火墙阻止了连接

解决方案:
```bash
# 检查Ollama服务状态
ps aux | grep ollama

# 确保Ollama监听在所有接口
echo "OLLAMA_HOST=0.0.0.0" >> ~/.ollama/.env
systemctl restart ollama  # 如果使用systemd
# 或
pkill ollama && ollama serve &  # 如果手动运行

# 检查防火墙
sudo ufw status
# 如需允许连接
sudo ufw allow 11434/tcp
```

### 2. 模型不存在

错误信息: `model "llama3" not found, try pulling it first`

解决方案:
```bash
# 列出可用模型
curl http://localhost:11434/api/tags | jq

# 拉取所需模型
ollama pull llama2
# 或
ollama pull llama3
```

### 3. Content-Type错误

错误信息: `415 Unsupported Media Type`

解决方案:
```bash
# 使用curl时添加Content-Type头
curl -X POST http://localhost:11435/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","messages":[{"role":"user","content":"Hello"}]}'
```

## 调试步骤

1. 检查Ollama服务和可用模型:
```bash
./check-ollama.sh
```

2. 使用自动检测模型的测试脚本:
```bash
./curl-test.sh
```

3. 查看代理服务日志:
```bash
docker logs ollama-unthink-proxy-proxy-1
```

4. 重启服务:
```bash
docker compose down
docker compose up -d
```

## 完整设置流程

如果需要从头开始设置:

1. 安装并配置Ollama:
```bash
./setup-ollama.sh
```

2. 启动代理服务:
```bash
docker compose up -d
```

3. 测试服务:
```bash
./curl-test.sh
```