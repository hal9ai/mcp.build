FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Gateway deps first so agent changes do not invalidate this layer.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./
# Every agent folder is self-contained; install whatever each one declares.
RUN for req in */requirements.txt; do \
      echo "Installing ${req}"; \
      pip install -r "${req}"; \
    done

EXPOSE 8080

CMD ["uvicorn", "mcp_server.server:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
