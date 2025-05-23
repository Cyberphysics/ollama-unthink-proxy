from flask import Flask, request, Response
from flask_cors import CORS
import requests
import json
import os
import logging
import time
from logging.handlers import RotatingFileHandler
import signal
import sys
from metrics import MetricsMiddleware, THINKING_CONTENT_REMOVED, OLLAMA_REQUEST_ERRORS, get_metrics

# Configure logging
log_dir = os.getenv("LOG_DIR", "logs")
os.makedirs(log_dir, exist_ok=True)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logger
logger = logging.getLogger("unthink-proxy")
logger.setLevel(getattr(logging, log_level))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# File handler
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "unthink-proxy.log"),
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

app = Flask(__name__)
resources = {
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": "*"
    }
}
CORS(app, resources=resources)

# 内联定义中间件，避免导入问题
class ContentTypeFixMiddleware:
    """Content-Type修复中间件"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # 检查Content-Type
        content_type = environ.get('CONTENT_TYPE', '')
        
        # 检查是否是LiteLLM请求
        user_agent = environ.get('HTTP_USER_AGENT', '')
        if 'litellm' in user_agent.lower() or not content_type:
            # 对于LiteLLM请求或没有Content-Type的请求，强制设置Content-Type
            logger.debug(f"修复LiteLLM请求的Content-Type: {content_type} -> application/json")
            environ['CONTENT_TYPE'] = 'application/json'
        elif not content_type or 'application/json' not in content_type.lower():
            logger.debug(f"修复Content-Type: {content_type} -> application/json")
            environ['CONTENT_TYPE'] = 'application/json'
        
        # 处理请求
        return self.app(environ, start_response)

# 应用中间件
app.wsgi_app = ContentTypeFixMiddleware(app.wsgi_app)
logger.info("已加载内联中间件")

# Apply metrics middleware
app.wsgi_app = MetricsMiddleware(app.wsgi_app)

# Configuration
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER") or "http://ollama:11434"
PROXY_PORT = int(os.getenv("PROXY_PORT") or 11434)
OPEN_THINK_TAG = os.getenv("OPEN_THINK_TAG") or "<" + "think>"
CLOSE_THINK_TAG = os.getenv("CLOSE_THINK_TAG") or "<" + "/think>"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT") or 60)
MAX_RETRIES = int(os.getenv("MAX_RETRIES") or 3)
RETRY_DELAY = int(os.getenv("RETRY_DELAY") or 1)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"


def process_thinking_content(
    message_content,
    thinking_started,
    thinking_finished
):
    """Process content based on thinking tags state"""
    if not message_content:
        return "", thinking_started, thinking_finished

    # Handle closing tag
    if CLOSE_THINK_TAG in message_content:
        thinking_started = False
        thinking_finished = True
        # If there's content after CLOSE_THINK_TAG, keep it
        content_after = message_content.split(CLOSE_THINK_TAG)[-1]
        # Increment metric for removed thinking content
        THINKING_CONTENT_REMOVED.inc()
        return content_after, thinking_started, thinking_finished

    # Handle opening tag
    if OPEN_THINK_TAG in message_content:
        thinking_started = True
        # If there's content before OPEN_THINK_TAG, keep it
        content_before = message_content.split(OPEN_THINK_TAG)[0]
        return content_before, thinking_started, thinking_finished

    # If we're in thinking mode, return empty
    if thinking_started:
        return "", thinking_started, thinking_finished

    return message_content, thinking_started, thinking_finished


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check if Ollama server is reachable
        response = requests.get(f"{OLLAMA_SERVER}/api/tags", timeout=5)
        if response.status_code == 200:
            return Response(json.dumps({"status": "healthy"}), status=200, mimetype='application/json')
        else:
            return Response(json.dumps({"status": "degraded", "message": "Ollama server returned non-200 status"}), 
                           status=503, mimetype='application/json')
    except requests.exceptions.RequestException as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response(json.dumps({"status": "unhealthy", "message": str(e)}), 
                       status=503, mimetype='application/json')


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return Response(get_metrics(), mimetype='text/plain')


@app.route('/api/<path:path>', methods=['POST'])
def proxy_api(path):
    """Proxy API requests to Ollama server"""
    start_time = time.time()
    request_id = f"{int(start_time)}-{os.getpid()}"
    
    # 记录请求头信息，帮助调试
    if DEBUG_MODE:
        logger.debug(f"[{request_id}] Request headers: {dict(request.headers)}")
        logger.debug(f"[{request_id}] Request path: {path}")
        logger.debug(f"[{request_id}] Request method: {request.method}")
        logger.debug(f"[{request_id}] Request data: {request.get_data()}")
    
    # 检查是否是LiteLLM请求
    user_agent = request.headers.get('User-Agent', '')
    is_litellm = 'litellm' in user_agent.lower()
    if is_litellm and DEBUG_MODE:
        logger.debug(f"[{request_id}] 检测到LiteLLM请求")
    
    # 检查Content-Type，但更宽容地处理
    content_type = request.headers.get('Content-Type', '')
    if DEBUG_MODE:
        logger.debug(f"[{request_id}] Received Content-Type: {content_type}")
    
    # 尝试解析请求数据，无论Content-Type是什么
    try:
        # 首先尝试使用request.json
        try:
            request_data = request.json
        except Exception as e:
            # 如果request.json解析失败，尝试手动解析
            logger.warning(f"[{request_id}] Failed to parse request.json: {str(e)}")
            data = request.get_data()
            if data:
                try:
                    request_data = json.loads(data)
                except json.JSONDecodeError as e:
                    # 对于LiteLLM请求，尝试特殊处理
                    if is_litellm:
                        logger.info(f"[{request_id}] 检测到LiteLLM请求，尝试特殊处理")
                        # 将请求体作为字符串读取
                        data_str = data.decode('utf-8')
                        # 尝试修复常见的JSON格式问题
                        try:
                            # 尝试将单引号替换为双引号
                            fixed_data = data_str.replace("'", "\"")
                            request_data = json.loads(fixed_data)
                            logger.info(f"[{request_id}] Successfully fixed and parsed JSON")
                        except Exception:
                            return Response(
                                json.dumps({"error": f"Invalid JSON format: {str(e)}"}),
                                status=400,
                                mimetype='application/json'
                            )
                    else:
                        logger.error(f"[{request_id}] Failed to parse request data: {str(e)}")
                        # 尝试修复常见的JSON格式问题
                        try:
                            # 尝试将单引号替换为双引号
                            fixed_data = data.decode('utf-8').replace("'", "\"")
                            request_data = json.loads(fixed_data)
                            logger.info(f"[{request_id}] Successfully fixed and parsed JSON")
                        except Exception:
                            return Response(
                                json.dumps({"error": f"Invalid JSON format: {str(e)}"}),
                                status=400,
                                mimetype='application/json'
                            )
            else:
                logger.error(f"[{request_id}] Empty request body")
                return Response(
                    json.dumps({"error": "Empty request body"}),
                    status=400,
                    mimetype='application/json'
                )
    except json.JSONDecodeError as e:
        logger.error(f"[{request_id}] Invalid JSON format: {str(e)}")
        return Response(
            json.dumps({"error": f"Invalid JSON format: {str(e)}"}),
            status=400,
            mimetype='application/json'
        )
    
    if DEBUG_MODE:
        logger.debug(f"[{request_id}] Request - Method: {request.method}")
        logger.debug(f"[{request_id}] Request - Path: {path}")
        logger.debug(f"[{request_id}] Request - Headers: {dict(request.headers)}")
        try:
            logger.debug(f"[{request_id}] Request - JSON: {request.json}")
        except Exception as e:
            logger.debug(f"[{request_id}] Error parsing JSON: {str(e)}")
    
    if path not in ['generate', 'chat', 'show']:
        logger.warning(f"[{request_id}] Invalid path requested: {path}")
        return Response('Not Found', status=404)

    # 获取请求数据
    try:
        request_data = request.json
    except Exception:
        # 如果request.json解析失败，尝试手动解析
        try:
            request_data = json.loads(request.get_data())
        except json.JSONDecodeError as e:
            logger.error(f"[{request_id}] Failed to parse JSON: {str(e)}")
            return Response(
                json.dumps({"error": "Invalid JSON format"}),
                status=400,
                mimetype='application/json'
            )
    
    if DEBUG_MODE:
        logger.debug(f"[{request_id}] Parsed request data: {request_data}")
    
    # 记录解析后的请求数据
    if DEBUG_MODE:
        logger.debug(f"[{request_id}] Parsed request data: {request_data}")
    
    # 处理LiteLLM特殊请求格式
    user_agent = request.headers.get('User-Agent', '')
    is_litellm = 'litellm' in user_agent.lower()
    
    # 如果是LiteLLM请求，检查是否需要转换格式
    if is_litellm and path == 'generate' and 'prompt' in request_data:
        logger.info(f"[{request_id}] 转换LiteLLM generate请求格式为chat格式")
        # 将generate格式转换为chat格式
        try:
            chat_data = {
                "model": request_data.get("model", ""),
                "messages": [
                    {"role": "user", "content": request_data.get("prompt", "")}
                ],
                "stream": request_data.get("stream", False)
            }
            
            # 如果有options，转换相关参数
            if "options" in request_data:
                options = request_data["options"]
                if "temperature" in options:
                    chat_data["temperature"] = options["temperature"]
                if "num_predict" in options:
                    chat_data["max_tokens"] = options["num_predict"]
            
            request_data = chat_data
            path = "chat"  # 改为使用chat API
            logger.info(f"[{request_id}] 已转换为chat格式: {request_data}")
        except Exception as e:
            logger.error(f"[{request_id}] 转换LiteLLM请求格式失败: {str(e)}")
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # 记录将要发送的请求
    if DEBUG_MODE:
        logger.debug(f"[{request_id}] Sending request to: {OLLAMA_SERVER}/api/{path}")
        logger.debug(f"[{request_id}] With headers: {headers}")
        logger.debug(f"[{request_id}] With data: {request_data}")
    
    # Retry logic for resilience
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{OLLAMA_SERVER}/api/{path}",
                json=request_data,
                headers=headers,
                stream=True,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()  # Raise exception for non-200 status codes
            break
        except requests.exceptions.RequestException as e:
            error_type = type(e).__name__
            OLLAMA_REQUEST_ERRORS.labels(error_type=error_type).inc()
            logger.error(f"[{request_id}] Request attempt {attempt+1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"[{request_id}] All retry attempts failed")
                return Response(json.dumps({"error": str(e)}), status=503, mimetype='application/json')

    def generate():
        thinking_started = False
        thinking_finished = False
        stripped_whitespace = False
        chunk_count = 0
        
        try:
            for chunk in response.iter_lines():
                chunk_count += 1
                
                if chunk:
                    try:
                        # Parse the JSON response
                        data = json.loads(chunk.decode('utf-8'))

                        # Check if this is a message with content
                        if (
                            'message' in data and
                            'content' in data['message'] and
                            data['message']['content'] != ''
                        ):
                            content = data['message']['content']
                            # Raw response from LLM
                            if DEBUG_MODE:
                                logger.debug(f"[{request_id}] Raw content: {content}")
                            
                            (
                                cleaned_content,
                                thinking_started,
                                thinking_finished
                            ) = process_thinking_content(
                                content,
                                thinking_started,
                                thinking_finished
                            )
                            
                            if thinking_finished and not stripped_whitespace:
                                cleaned_content = cleaned_content.strip()
                                if (
                                    cleaned_content and
                                    not cleaned_content.isspace()
                                ):
                                    stripped_whitespace = True
                            
                            if cleaned_content == '':
                                continue

                            # Update the content in the data
                            data['message']['content'] = cleaned_content
                            yield json.dumps(data).encode('utf-8') + b'\n'
                        else:
                            # Forward non-content messages (like 'done' messages)
                            yield chunk + b'\n'

                    except json.JSONDecodeError as e:
                        logger.error(f"[{request_id}] JSON decode error: {str(e)}")
                        yield chunk + b'\n'
                        
        except Exception as e:
            logger.error(f"[{request_id}] Error in generate function: {str(e)}")
            # Return an error message that client can understand
            error_data = {"error": str(e)}
            yield json.dumps(error_data).encode('utf-8') + b'\n'
        finally:
            duration = time.time() - start_time
            logger.info(f"[{request_id}] Request completed in {duration:.2f}s, processed {chunk_count} chunks")

    return Response(
        generate(),
        mimetype='application/json',
        headers={
            'X-Accel-Buffering': 'no',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'X-Request-ID': request_id
        }
    )


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'OPTIONS'])
def catch_all(path):
    """Catch-all route to proxy all other requests to Ollama server"""
    request_id = f"{int(time.time())}-{os.getpid()}"
    
    if request.method == 'OPTIONS':
        return Response('', 204)

    try:
        resp = requests.request(
            method=request.method,
            url=f"{OLLAMA_SERVER}/{path}",
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=REQUEST_TIMEOUT,
            headers={
                key: value for key, value in request.headers if key != 'Host'
            }
        )

        excluded_headers = [
            'content-encoding',
            'content-length',
            'transfer-encoding',
            'connection'
        ]
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                if name.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, headers)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[{request_id}] Error in catch_all route: {str(e)}")
        return Response(json.dumps({"error": str(e)}), status=503, mimetype='application/json')


def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    logger.info("Received shutdown signal, exiting...")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"Starting proxy server on port {PROXY_PORT}")
    logger.info(f"Forwarding requests to {OLLAMA_SERVER}")
    logger.info(f"Log level set to {log_level}")
    
    # Use production-ready WSGI server if available
    try:
        from waitress import serve
        logger.info("Using Waitress WSGI server")
        serve(app, host="0.0.0.0", port=PROXY_PORT)
    except ImportError:
        logger.warning("Waitress not installed, falling back to Flask development server")
        app.run(host="0.0.0.0", port=PROXY_PORT, debug=False)