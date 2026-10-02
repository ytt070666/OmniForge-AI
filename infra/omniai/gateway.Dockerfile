FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY services/omniai_gateway/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/omniops apps/omniops
COPY extensions/omnirag extensions/omnirag
COPY omniai_platform omniai_platform
COPY services/omniai_gateway services/omniai_gateway
CMD ["python", "-m", "services.omniai_gateway.main", "--host", "0.0.0.0", "--port", "8090"]
