"""
Transformer-based sentiment model for continuous urgency score S in [0, 1].

Uses a pre-trained sentiment classifier; negative sentiment probability is mapped
to urgency (higher negative = higher S). Output is regression-style S ∈ [0, 1].
"""

import torch

# Lazy-loaded model and tokenizer
_model = None
_tokenizer = None

# Default: DistilBERT fine-tuned on SST-2 (binary sentiment)
DEFAULT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"


def _get_model(model_name: str = DEFAULT_MODEL):
    global _model, _tokenizer
    if _model is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForSequenceClassification.from_pretrained(model_name)
        _model.eval()
    return _model, _tokenizer


def compute_urgency_score(text: str, model_name: str = DEFAULT_MODEL, max_length: int = 512) -> float:
    """
    Compute continuous urgency score S in [0, 1] using transformer sentiment.

    Negative sentiment probability is used as the urgency proxy (e.g. "broken ASAP"
    tends to be negative → high S). Model output is softmax over [negative, positive];
    we use P(negative) as S.
    """
    if not text or not text.strip():
        return 0.0

    model, tokenizer = _get_model(model_name)
    inputs = tokenizer(
        text.strip(),
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
        padding=True,
    )

    with torch.no_grad():
        logits = model(**inputs).logits

    # SST-2 / DistilBERT sentiment: index 0 = negative, 1 = positive
    probs = torch.softmax(logits, dim=-1).squeeze()
    if probs.dim() == 0:
        probs = probs.unsqueeze(0)
    neg_prob = float(probs[0].item())
    return round(min(1.0, max(0.0, neg_prob)), 4)
