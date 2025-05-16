#!/usr/bin/env python3
"""
使用OpenAI客户端测试完整响应
"""
import openai
import sys
import json
import requests
import time

# 配置
OLLAMA_URL = "http://10.252.17.12:11434"  # 原始Ollama服务
PROXY_URL = "http://localhost:11435"       # Unthink代理服务
MODEL = None  # 将自动检测

def get_available_model():
    """获取第一个可用的模型"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            if models:
                return models[0]['name']
    except Exception as e:
        print(f"获取模型失败: {e}")
    return None

def test_with_openai_client(base_url, model):
    """使用OpenAI客户端测试"""
    print(f"\n使用OpenAI客户端测试 {base_url}...")
    
    # 创建客户端
    client = openai.OpenAI(
        base_url=base_url,
        api_key="fake-key"  # Ollama不需要真实的API密钥
    )
    
    # 发送请求
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "请简要介绍Python语言的主要特点，不超过100字。"}
            ],
            stream=False  # 关键参数：请求完整响应而非流式响应
        )
        end_time = time.time()
        
        print(f"响应时间: {end_time - start_time:.2f}秒")
        print(f"响应内容:\n{response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"请求失败: {e}")
        return False

if __name__ == "__main__":
    # 获取可用模型
    MODEL = get_available_model()
    if not MODEL:
        print("错误: 未找到可用模型，请先拉取模型")
        print("例如: ollama pull llama2")
        sys.exit(1)
    
    print(f"使用模型: {MODEL}")
    
    # 测试原始Ollama服务
    test_with_openai_client(OLLAMA_URL, MODEL)
    
    # 测试Unthink代理服务
    test_with_openai_client(PROXY_URL, MODEL)