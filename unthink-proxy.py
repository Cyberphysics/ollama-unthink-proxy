from flask import Flask, request, Response
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
resources = {
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": "*"
    }
}
CORS(app, resources=resources)

# Configuration
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER") or "http://ollama:11434"
PROXY_PORT = os.getenv("PROXY_PORT") or 11434
OPEN_THINK_TAG = os.getenv("OPEN_THINK_TAG") or "<" + "think>"
CLOSE_THINK_TAG = os.getenv("CLOSE_THINK_TAG") or "<" + "/think>"


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


@app.route('/api/<path:path>', methods=['POST'])
def proxy_api(path):
    print(f"Debug Request - Method: {request.method}", flush=True)
    print(f"Debug Request - Path: {path}", flush=True)
    print(f"Debug Request - Full Path: {request.path}", flush=True)
    print(f"Debug Request - Headers: {dict(request.headers)}", flush=True)
    print(f"Debug Request - JSON: {request.json}", flush=True)
    if path not in ['generate', 'chat', 'show']:
        return Response('Not Found', status=404)

    response = requests.post(
        f"{OLLAMA_SERVER}/api/{path}",
        json=request.json,
        stream=True
    )

    def generate():
        thinking_started = False
        thinking_finished = False
        stripped_whitespace = False
        for chunk in response.iter_lines():

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
                        print(content, end='', flush=True)
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

                except json.JSONDecodeError:
                    yield chunk + b'\n'

    return Response(
        generate(),
        mimetype='application/json',
        headers={
            'X-Accel-Buffering': 'no',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json'
        }
    )


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'OPTIONS'])
def catch_all(path):
    if request.method == 'OPTIONS':
        return Response('', 204)

    resp = requests.request(
        method=request.method,
        url=f"{OLLAMA_SERVER}/{path}",
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
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


if __name__ == '__main__':
    print(f"Starting proxy server on port {PROXY_PORT}")
    print(f"Forwarding requests to {OLLAMA_SERVER}")
    app.run(host="0.0.0.0", port=PROXY_PORT, debug=False)
