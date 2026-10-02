from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from labs.tensorflow_lab.features import text_features
from omniai_platform.http_contract import install_http_contract

app = FastAPI(title="OmniAI TensorFlow Severity Service", version="1.0.0")
install_http_contract(app)
MODEL_PATH = Path(os.getenv("OMNIAI_TF_MODEL", "artifacts/omniai/tensorflow/severity.keras"))
_model = None


class SeverityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=8000)


def _load():
    global _model
    if _model is not None:
        return _model
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError("TensorFlow is not installed") from exc
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"model artifact not found: {MODEL_PATH}")
    _model = tf.keras.models.load_model(MODEL_PATH)
    return _model


@app.get("/health")
def health():
    try:
        import tensorflow as tf
        version = tf.__version__
        installed = True
    except ImportError:
        version = None
        installed = False
    return {"ok": True, "service": "omniai-tensorflow", "version": app.version, "framework": "TensorFlow", "installed": installed, "framework_version": version, "model_ready": MODEL_PATH.is_file()}


@app.post("/api/v1/severity")
def classify(payload: SeverityRequest):
    try:
        import numpy as np
        model = _load()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    probs = model.predict(np.asarray([text_features(payload.text)], dtype="float32"), verbose=0)[0]
    labels = ["low", "medium", "high", "critical"]
    index = int(probs.argmax())
    return {"severity": labels[index], "probability": float(probs[index]), "synthetic_model": True}
