FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY services/omniai_tensorflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY omniai_platform omniai_platform
COPY labs/tensorflow_lab labs/tensorflow_lab
COPY services/omniai_tensorflow services/omniai_tensorflow
COPY artifacts/omniai/tensorflow artifacts/omniai/tensorflow
CMD ["uvicorn", "services.omniai_tensorflow.app:app", "--host", "0.0.0.0", "--port", "8095"]
