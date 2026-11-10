#!/usr/bin/env python3
"""CLI Prediction Tool for CJP Protest Narrative Triage.

Predicts narrative category and class probabilities for input claim texts.
MANDATORY NOTICE: Feasibility pilot on documented claim records; not for detection
or content moderation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any
import joblib
import numpy as np

MANDATORY_WARNING = (
    "WARNING: Feasibility pilot on documented claim records; not for detection or content moderation. "
    "Scores are unstable and are not evidence that AI propaganda can be detected."
)

SMOKE_TEST_EXAMPLES = [
    "Drone footage shows 1 million students gathering at Jantar Mantar demanding NEET re-exam.",
    "Delhi police baton charged and critically injured peaceful student protesters at Connaught Place.",
    "Protesters chanted anti-national and pro-Pakistan slogans during the CJP rally.",
    "Education Minister Dharmendra Pradhan submitted his resignation letter after protest escalation.",
    "Students set a DTC bus on fire and threw stones at police barricades near ITO.",
]


def load_model(model_path: Path | None = None) -> dict[str, Any]:
    """Loads the serialized model payload from disk."""
    if model_path is None:
        model_path = Path("outputs/final_model/model.joblib")
    if not model_path.exists():
        fallback_path = Path("outputs/final_model/tfidf_char_lr.joblib")
        if fallback_path.exists():
            model_path = fallback_path
        else:
            raise FileNotFoundError(f"Model file not found at {model_path} or {fallback_path}")

    payload = joblib.load(model_path)
    return payload


_MODEL_CACHE: dict[str, Any] = {}

def extract_embeddings_for_texts(
    hf_model_name: str,
    texts: list[str],
) -> np.ndarray:
    """Extracts mean-pooled embeddings using Hugging Face transformers."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    if hf_model_name not in _MODEL_CACHE:
        device = torch.device("mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu"))
        tokenizer = AutoTokenizer.from_pretrained(hf_model_name)
        try:
            model = AutoModel.from_pretrained(hf_model_name, low_cpu_mem_usage=True).to(device)
        except TypeError:
            model = AutoModel.from_pretrained(hf_model_name).to(device)
        model.eval()
        _MODEL_CACHE[hf_model_name] = (tokenizer, model, device)
    else:
        tokenizer, model, device = _MODEL_CACHE[hf_model_name]

    all_embs = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        encoded = tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**encoded)
            mask = encoded["attention_mask"].unsqueeze(-1).expand(out.last_hidden_state.size()).float()
            sum_embs = torch.sum(out.last_hidden_state * mask, dim=1)
            sum_mask = torch.clamp(mask.sum(dim=1), min=1e-9)
            mean_pooled = sum_embs / sum_mask
            all_embs.append(mean_pooled.cpu().numpy())

    return np.vstack(all_embs)


def predict_claim(
    text: str,
    model_payload: dict[str, Any],
) -> dict[str, Any]:
    """Generates prediction and probability distribution for a single claim text."""
    classes = model_payload["classes"]
    arch = model_payload.get("architecture", "")

    if arch == "frozen_encoder_logistic_regression":
        hf_name = model_payload["hf_model_name"]
        feats = extract_embeddings_for_texts(hf_name, [text])
        scaler = model_payload["scaler"]
        feats_scaled = scaler.transform(feats)
        clf = model_payload["clf"]
        probs = clf.predict_proba(feats_scaled)[0]
        top_idx = int(np.argmax(probs))
        top_label = classes[top_idx]
    elif arch == "pipeline" or "pipeline" in model_payload:
        pipe = model_payload["pipeline"]
        probs = pipe.predict_proba([text])[0]
        top_idx = int(np.argmax(probs))
        top_label = classes[top_idx]
    else:
        raise ValueError(f"Unsupported model payload architecture: {arch}")

    prob_dict = {classes[i]: round(float(probs[i]), 4) for i in range(len(classes))}
    return {
        "text": text,
        "predicted_label": top_label,
        "confidence": round(float(probs[top_idx]), 4),
        "probabilities": prob_dict,
        "warning": MANDATORY_WARNING,
    }


def run_smoke_test(model_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Runs prediction on 5 example claims to verify pipeline stability."""
    print("\n" + "=" * 70)
    print("RUNNING SMOKE TEST ON 5 EXAMPLE CLAIMS")
    print("=" * 70)
    results = []
    for i, claim in enumerate(SMOKE_TEST_EXAMPLES, 1):
        res = predict_claim(claim, model_payload)
        results.append(res)
        print(f"\n[Claim {i}]: \"{claim}\"")
        print(f"  Predicted Label: {res['predicted_label']} (Confidence: {res['confidence']:.2%})")
        print(f"  Class Probabilities: {res['probabilities']}")
    print("\n" + "-" * 70)
    print(f"NOTICE: {MANDATORY_WARNING}")
    print("-" * 70)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict narrative framing for protest claim texts.")
    parser.add_argument("text", nargs="?", default=None, help="Claim text to evaluate.")
    parser.add_argument("--model-path", type=Path, default=None, help="Path to serialized model.joblib.")
    parser.add_argument("--smoke-test", action="store_true", help="Run smoke test on 5 canonical example claims.")
    parser.add_argument("--lightweight", action="store_true", help="Use lightweight TF-IDF model instead of transformer.")
    args = parser.parse_args()

    model_path = args.model_path
    if args.lightweight and model_path is None:
        model_path = Path("outputs/final_model/tfidf_char_lr.joblib")

    try:
        model_payload = load_model(model_path)
    except Exception as e:
        sys.exit(f"Failed to load model: {e}")

    if args.smoke_test or args.text is None:
        run_smoke_test(model_payload)
        return

    result = predict_claim(args.text, model_payload)
    print("\n" + "=" * 70)
    print(f"Claim Text: \"{result['text']}\"")
    print(f"Predicted Narrative: {result['predicted_label']} ({result['confidence']:.2%})")
    print("Class Probabilities:")
    for cls_name, p in result["probabilities"].items():
        print(f"  - {cls_name:25s}: {p:.4f}")
    print("\n" + "-" * 70)
    print(result["warning"])
    print("-" * 70)


if __name__ == "__main__":
    main()
