# Ubuntu 18.04 GPU设置指南

这个指南专为在Ubuntu 18.04上设置Ollama Unthink Proxy与NVIDIA GPU支持而设计。

## 前提条件

确保已安装NVIDIA驱动：

```bash
nvidia-smi
```

如果命令不可用，请先安装NVIDIA驱动：

```bash
sudo apt-get update
sudo apt-get install -y nvidia-driver-470  # 或其他适合你GPU的版本
sudo reboot
```

## 安装NVIDIA Container Toolkit

1. 运行专为Ubuntu 18.04设计的安装脚本：

```bash
chmod +x nvidia-docker-ubuntu18.sh
sudo ./nvidia-docker-ubuntu18.sh
```

2. 验证安装：

```bash
chmod +x gpu-test-ubuntu18.sh
./gpu-test-ubuntu18.sh
```

## 配置Docker Compose

docker-compose.yml文件已经针对Ubuntu 18.04进行了优化，使用`runtime: nvidia`配置。

## 启动服务

```bash
docker compose up -d
```

## 故障排除

如果遇到问题，请尝试以下步骤：

1. 检查NVIDIA驱动是否正常工作：
   ```bash
   nvidia-smi
   ```

2. 检查Docker是否能识别NVIDIA运行时：
   ```bash
   docker info | grep -i nvidia
   ```

3. 尝试直接运行CUDA容器：
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu18.04 nvidia-smi
   ```

4. 如果上述命令失败，尝试使用设备映射方式：
   ```bash
   # 编辑docker-compose.yml，注释掉runtime: nvidia，取消注释devices部分
   ```

5. 检查Docker和nvidia-docker2版本：
   ```bash
   docker --version
   apt list --installed | grep nvidia-docker
   ```