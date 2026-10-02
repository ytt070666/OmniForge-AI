from __future__ import annotations

import json
from pathlib import Path

from features import text_features

SAMPLES = [
    ("routine patch completed successfully", 0),
    ("minor warning on one worker", 1),
    ("api timeout rate increased after deployment", 2),
    ("database unavailable critical errors across cluster", 3),
    ("cpu usage elevated but service healthy", 1),
    ("dns beacon attack detected on gateway", 3),
    ("memory pressure causes intermittent timeout", 2),
    ("scheduled database maintenance", 0),
] * 20


def main() -> None:
    try:
        import numpy as np
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit("Install labs/tensorflow_lab/requirements.txt first") from exc

    x = np.asarray([text_features(text) for text, _ in SAMPLES], dtype="float32")
    y = np.asarray([label for _, label in SAMPLES], dtype="int32")
    ds = tf.data.Dataset.from_tensor_slices((x, y)).shuffle(len(SAMPLES), seed=7).batch(16)
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(x.shape[1],)),
        tf.keras.layers.Dense(24, activation="relu"),
        tf.keras.layers.Dense(4, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    history = model.fit(ds, epochs=8, verbose=0)
    evaluation = model.evaluate(ds, verbose=0, return_dict=True)
    out = Path("artifacts/omniai/tensorflow/severity.keras")
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(out)
    meta = {
        "artifact": str(out),
        "samples": len(SAMPLES),
        "synthetic_only": True,
        "final_training_accuracy": float(history.history["accuracy"][-1]),
        "evaluation": {key: float(value) for key, value in evaluation.items()},
        "claim_boundary": "training plumbing metric only; not a production benchmark",
    }
    (out.parent / "training_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
