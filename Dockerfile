FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY unthink-proxy.py /app/

CMD ["python3", "/app/unthink-proxy.py"]
