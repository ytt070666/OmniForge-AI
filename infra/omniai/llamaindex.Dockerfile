FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY services/omniai_llamaindex/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY omniai_platform omniai_platform
COPY services/omniai_llamaindex services/omniai_llamaindex
CMD ["uvicorn", "services.omniai_llamaindex.app:app", "--host", "0.0.0.0", "--port", "8094"]
