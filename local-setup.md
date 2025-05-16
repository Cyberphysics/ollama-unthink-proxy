# 使用本地Ollama服务的设置指南

这个指南说明如何将Unthink Proxy连接到主机上已安装的Ollama服务。

## 前提条件

1. 确保主机上已安装并运行Ollama服务：
   ```bash
   # 检查Ollama服务状态
   systemctl status ollama
   
   # 如果未运行，启动服务
   systemctl start ollama
   ```

2. 确保Ollama服务监听在所有网络接口上：
   ```bash
   # 编辑Ollama配置
   vi ~/.ollama/.env
   
   # 添加或修改以下行
   OLLAMA_HOST=0.0.0.0
   
   # 重启Ollama服务
   systemctl restart ollama
   ```

3. 验证Ollama服务可访问：
   ```bash
   curl http://10.252.17.12:11434/api/tags
   ```

## 启动Unthink Proxy

```bash
docker compose up -d
```

这将启动：
- Unthink Proxy (连接到主机Ollama服务)
- Prometheus
- Grafana

## 验证设置

```bash
# 检查代理服务是否正常运行
curl http://localhost:11434/health

# 测试代理功能
curl -X POST http://localhost:11434/api/chat -d '{
  "model": "llama3",
  "messages": [{"role": "user", "content": "Hello, world!"}]
}'
```

## 故障排除

如果遇到连接问题：

1. 确认主机防火墙允许容器访问11434端口：
   ```bash
   # 允许内部网络访问Ollama端口
   sudo ufw allow from 172.16.0.0/12 to any port 11434
   ```

2. 检查Ollama服务日志：
   ```bash
   journalctl -u ollama
   ```

3. 尝试使用不同的网络模式：
   ```bash
   # 编辑docker-compose.yml，添加网络模式
   # 在proxy服务下添加：
   # network_mode: "host"
   ```