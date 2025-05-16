#!/usr/bin/env python3
"""
LiteLLM适配器 - 用于测试LiteLLM与Unthink_proxy的集成
"""
import requests
import json
import sys
import time

# 配置
PROXY_URL = "http://localhost:11435"  # Unthink代理服务
MODEL = None  # 将自动检测

def get_available_model():
    """获取第一个可用的模型"""
    try:
        response = requests.get(f"{PROXY_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            if models:
                return models[0]['name']
    except Exception as e:
        print(f"获取模型失败: {e}")
    return "llama2"  # 默认模型

def simulate_litellm_request():
    """模拟LiteLLM发送的请求格式"""
    model = get_available_model()
    print(f"使用模型: {model}")
    
    # LiteLLM发送的请求格式
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": "请简要介绍Python语言的主要特点，不超过100字。"}
        ],
        "stream": False
    }
    
    # 测试不同的Content-Type
    content_types = [
        "application/json",  # 标准JSON
        "application/json; charset=utf-8",  # 带字符集的JSON
        None,  # 不设置Content-Type
        "text/plain"  # 纯文本
    ]
    
    for content_type in content_types:
        print(f"\n测试Content-Type: {content_type}")
        
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{PROXY_URL}/api/chat",
                headers=headers,
                data=json.dumps(data) if content_type != "application/json" else None,
                json=data if content_type == "application/json" else None
            )
            end_time = time.time()
            
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {end_time - start_time:.2f}秒")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    content = result.get('message', {}).get('content', '')
                    print(f"响应内容: {content[:100]}...")
                except Exception as e:
                    print(f"解析响应失败: {e}")
                    print(f"原始响应: {response.text[:200]}...")
            else:
                print(f"请求失败: {response.text}")
        except Exception as e:
            print(f"请求异常: {e}")

if __name__ == "__main__":
    simulate_litellm_request()