#!/usr/bin/env python3
"""
测试脚本：请求完整的回答，而不是流式响应
"""
import requests
import json
import sys
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

def test_complete_response(url, model):
    """测试完整响应"""
    print(f"\n测试 {url} 的完整响应...")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "请简要介绍Python语言的主要特点，不超过100字。"
            }
        ],
        "stream": False  # 关键参数：请求完整响应而非流式响应
    }
    
    start_time = time.time()
    response = requests.post(f"{url}/api/chat", headers=headers, json=data)
    end_time = time.time()
    
    if response.status_code == 200:
        result = response.json()
        content = result.get('message', {}).get('content', '')
        print(f"响应时间: {end_time - start_time:.2f}秒")
        print(f"响应内容:\n{content}")
        return True
    else:
        print(f"请求失败: {response.status_code}")
        print(response.text)
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
    test_complete_response(OLLAMA_URL, MODEL)
    
    # 测试Unthink代理服务
    test_complete_response(PROXY_URL, MODEL)