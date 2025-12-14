# Flow Studio - Lightweight container for flow visualization
#
# Build:   docker build -t flowstudio .
# Run:     docker run -p 5000:5000 -v $(pwd)/config:/app/config flowstudio

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir . gunicorn

# Copy application code
COPY flowstudio/ ./flowstudio/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 flowstudio && chown -R flowstudio:flowstudio /app
USER flowstudio

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "flowstudio.server:create_app()"]
