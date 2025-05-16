#!/bin/bash
# 安装NVIDIA Container Toolkit

# 添加NVIDIA软件包仓库
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 更新软件包列表
sudo apt-get update

# 安装nvidia-docker2
sudo apt-get install -y nvidia-docker2

# 重启Docker服务
sudo systemctl restart docker

# 验证安装
echo "验证NVIDIA Container Toolkit安装:"
sudo docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

echo "如果上面显示了GPU信息，则安装成功"
echo "现在可以运行: docker compose up -d"