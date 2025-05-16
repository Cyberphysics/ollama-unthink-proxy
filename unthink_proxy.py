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
    
    if DEBUG_MODE:
        logger.debug(f"[{request_id}] Request - Method: {request.method}")
        logger.debug(f"[{request_id}] Request - Path: {path}")
        logger.debug(f"[{request_id}] Request - Headers: {dict(request.headers)}")
        logger.debug(f"[{request_id}] Request - JSON: {request.json}")
    
    if path not in ['generate', 'chat', 'show']:
        logger.warning(f"[{request_id}] Invalid path requested: {path}")
        return Response('Not Found', status=404)

    # Retry logic for resilience
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{OLLAMA_SERVER}/api/{path}",
                json=request.json,
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