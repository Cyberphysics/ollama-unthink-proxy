#!/usr/bin/env python3
"""
使用LiteLLM库测试与Unthink_proxy的集成
"""
import os
import sys
import time

# 设置LiteLLM环境变量
os.environ["OPENAI_API_KEY"] = "fake-key"
os.environ["OPENAI_API_BASE"] = "http://localhost:11435"

try:
    from litellm import completion
except ImportError:
    print("请先安装LiteLLM: pip install litellm")
    sys.exit(1)

def test_litellm_completion():
    """测试LiteLLM completion API"""
    print("测试LiteLLM与Unthink_proxy的集成...")
    
    try:
        # 启用调试模式
        import litellm
        litellm.set_verbose = True
        
        # 发送请求
        start_time = time.time()
        response = completion(
            model="llama2",  # 使用默认模型，实际模型由Ollama决定
            messages=[
                {"role": "user", "content": "请简要介绍Python语言的主要特点，不超过100字。"}
            ],
            api_base="http://localhost:11435",
            api_key="fake-key"
        )
        end_time = time.time()
        
        print(f"响应时间: {end_time - start_time:.2f}秒")
        print(f"响应内容:\n{response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"请求失败: {e}")
        return False

if __name__ == "__main__":
    test_litellm_completion()