FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_DIR=/var/log/unthink-proxy \
    LOG_LEVEL=INFO

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Create log directory and set permissions
RUN mkdir -p ${LOG_DIR} && \
    chown -R appuser:appgroup ${LOG_DIR}

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY unthink_proxy.py /app/
COPY metrics.py /app/
COPY middleware.py /app/
COPY tests/ /app/tests/

# Create health check script
RUN echo '#!/bin/sh\nwget -q -O- http://localhost:${PROXY_PORT:-11434}/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Set permissions
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 11434

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD ["/app/healthcheck.sh"]

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:11434", "--workers", "4", "--timeout", "120", "unthink_proxy:app"]
