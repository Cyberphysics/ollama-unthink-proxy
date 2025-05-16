#!/usr/bin/env python3
"""
Flask中间件 - 用于处理请求和响应
"""
from flask import request, g
import time
import logging

logger = logging.getLogger("unthink-proxy")

class RequestLoggingMiddleware:
    """请求日志中间件"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # 在请求处理前
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        request_id = f"{int(time.time())}-{environ.get('wsgi.input', '')}"
        
        # 记录请求信息
        logger.info(f"[{request_id}] Request: {method} {path}")
        
        # 记录请求头
        headers = {k: v for k, v in environ.items() if k.startswith('HTTP_')}
        logger.debug(f"[{request_id}] Headers: {headers}")
        
        # 自定义响应开始函数
        def custom_start_response(status, headers, exc_info=None):
            logger.info(f"[{request_id}] Response: {status}")
            logger.debug(f"[{request_id}] Response headers: {headers}")
            return start_response(status, headers, exc_info)
        
        # 处理请求
        return self.app(environ, custom_start_response)


class ContentTypeFixMiddleware:
    """Content-Type修复中间件"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # 检查Content-Type
        content_type = environ.get('CONTENT_TYPE', '')
        
        # 如果没有Content-Type或不是application/json，添加它
        if not content_type or 'application/json' not in content_type.lower():
            logger.debug(f"修复Content-Type: {content_type} -> application/json")
            environ['CONTENT_TYPE'] = 'application/json'
        
        # 处理请求
        return self.app(environ, start_response)