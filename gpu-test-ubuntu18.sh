#!/bin/bash
# 测试Docker中的GPU支持 - 针对Ubuntu 18.04优化

echo "检查NVIDIA驱动安装情况:"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
else
    echo "未找到nvidia-smi命令，请确保NVIDIA驱动已正确安装"
    exit 1
fi

echo -e "\n检查Docker是否支持GPU:"
if docker info | grep -i nvidia > /dev/null; then
    echo "Docker已启用NVIDIA支持"
else
    echo "Docker未启用NVIDIA支持，请安装nvidia-docker2"
    exit 1
fi

echo -e "\n尝试使用适合Ubuntu 18.04的CUDA镜像测试GPU:"

echo -e "\n尝试CUDA 11.4 (Ubuntu 18.04):"
docker run --rm --gpus all nvidia/cuda:11.4.3-base-ubuntu18.04 nvidia-smi || echo "CUDA 11.4 测试失败"

echo -e "\n尝试CUDA 11.0 (Ubuntu 18.04):"
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu18.04 nvidia-smi || echo "CUDA 11.0 测试失败"

echo -e "\n尝试CUDA 10.2 (Ubuntu 18.04):"
docker run --rm --gpus all nvidia/cuda:10.2-base-ubuntu18.04 nvidia-smi || echo "CUDA 10.2 测试失败"

echo -e "\n如果上面任何一个测试成功显示了GPU信息，则GPU支持正常"
echo "现在可以运行: docker compose up -d"