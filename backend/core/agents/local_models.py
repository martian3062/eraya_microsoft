"""
LocalModelRegistry — catalog and lazy-load small HuggingFace models.

Sources:
  local  — downloaded once, runs on CPU (or CUDA if available)
  groq   — Groq cloud API (requires GROQ_API_KEY)

Supported local models (all < 2 GB in fp16 or 4-bit):
  flan-t5-small   google/flan-t5-small        80M   seq2seq
  t5-small        t5-small                    60M   seq2seq
  distilgpt2      distilgpt2                  82M   causal
  flame-3b        microsoft/FLAME-3B          3B    causal (4-bit)
  baby-llama      Felladrin/BabyLlama-58M     58M   causal
  gemma-3-1b      google/gemma-3-1b-it        1B    causal

Usage:
    from core.agents.local_models import get_model, registry_info
    m = get_model("flan-t5-small")
    text = m.generate("Plan an action for: high CPU load")
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("eraya.local_models")


# ─── Model entry ──────────────────────────────────────────────────────────────

@dataclass
class ModelEntry:
    model_id: str
    display_name: str
    params_m: int           # millions of parameters
    size_mb: int            # approx download size (0 = cloud)
    task: str               # "text2text-generation" | "text-generation"
    source: str             # "local" | "groq"
    description: str
    badge: str              # UI badge label
    max_new_tokens: int = 128
    quantized: bool = False
    _pipeline: Any = field(default=None, init=False, repr=False)

    def load(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline as hf_pipeline
            logger.info("Loading model %s …", self.model_id)
            kwargs: dict[str, Any] = {
                "task": self.task,
                "model": self.model_id,
            }
            if self.quantized:
                from transformers import BitsAndBytesConfig
                kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
            else:
                kwargs["device"] = "cpu"

            token = os.environ.get("HUGGINGFACE_TOKEN") or None
            if token:
                kwargs["token"] = token

            self._pipeline = hf_pipeline(**kwargs)
            logger.info("Loaded %s.", self.model_id)
        except Exception as exc:
            logger.error("Failed to load %s: %s", self.model_id, exc)
            raise
        return self._pipeline

    def generate(self, prompt: str) -> str:
        pipe = self.load()
        try:
            if self.task == "text2text-generation":
                out = pipe(prompt, max_new_tokens=self.max_new_tokens, do_sample=False)
                return out[0]["generated_text"]
            else:
                out = pipe(
                    prompt,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=True,
                    temperature=0.1,
                    pad_token_id=pipe.tokenizer.eos_token_id,
                )
                full: str = out[0]["generated_text"]
                return full[len(prompt):].strip()
        except Exception as exc:
            logger.error("Generation error for %s: %s", self.model_id, exc)
            return ""

    def to_dict(self) -> dict:
        return {
            "key": "",                          # filled by registry_info()
            "model_id": self.model_id,
            "display_name": self.display_name,
            "params_m": self.params_m,
            "size_mb": self.size_mb,
            "task": self.task,
            "source": self.source,
            "description": self.description,
            "badge": self.badge,
            "max_new_tokens": self.max_new_tokens,
            "quantized": self.quantized,
            "loaded": self._pipeline is not None,
            "available": True,
        }


# ─── Local model catalog ───────────────────────────────────────────────────────

LOCAL_MODELS: dict[str, ModelEntry] = {
    "flan-t5-small": ModelEntry(
        model_id="google/flan-t5-small",
        display_name="Flan-T5 Small",
        params_m=80,
        size_mb=308,
        task="text2text-generation",
        source="local",
        badge="Seq2Seq",
        description="Google Flan-T5 instruction-tuned. Excellent for structured prompts, "
                    "Q&A, and planning tasks without a GPU.",
    ),
    "t5-small": ModelEntry(
        model_id="t5-small",
        display_name="T5 Small",
        params_m=60,
        size_mb=242,
        task="text2text-generation",
        source="local",
        badge="Seq2Seq",
        description="Google T5 Small seq2seq. Fastest local model for CPU inference. "
                    "Good baseline for text transformation tasks.",
    ),
    "distilgpt2": ModelEntry(
        model_id="distilgpt2",
        display_name="DistilGPT-2",
        params_m=82,
        size_mb=353,
        task="text-generation",
        source="local",
        badge="Causal LM",
        description="Distilled GPT-2 by HuggingFace. Small causal LM, great for "
                    "free-form text generation and quick iteration.",
    ),
    "flame-3b": ModelEntry(
        model_id="microsoft/FLAME-3B",
        display_name="FLAME 3B",
        params_m=3000,
        size_mb=6144,
        task="text-generation",
        source="local",
        badge="Causal LM",
        description="Microsoft FLAME — structured-reasoning LM designed for formula and "
                    "tabular data understanding. 4-bit quant recommended.",
        max_new_tokens=128,
        quantized=True,
    ),
    "baby-llama": ModelEntry(
        model_id="Felladrin/BabyLlama-58M",
        display_name="BabyLlama 58M",
        params_m=58,
        size_mb=220,
        task="text-generation",
        source="local",
        badge="Causal LM",
        description="Tiny Llama-architecture model, 58M parameters. Runs on any CPU, "
                    "no GPU needed. Ideal for rapid local testing.",
        max_new_tokens=80,
    ),
    "gemma-3-1b": ModelEntry(
        model_id="google/gemma-3-1b-it",
        display_name="Gemma 3 1B-IT",
        params_m=1000,
        size_mb=2048,
        task="text-generation",
        source="local",
        badge="Instruction",
        description="Google Gemma 3 instruction-tuned 1B — smallest production-quality "
                    "Gemma 3. Requires HuggingFace token for gated access.",
        max_new_tokens=256,
    ),
}

# ─── Groq cloud model catalog ─────────────────────────────────────────────────

GROQ_MODELS: dict[str, ModelEntry] = {
    "groq-llama-3.3-70b": ModelEntry(
        model_id="llama-3.3-70b-versatile",
        display_name="LLaMA 3.3 70B",
        params_m=70_000,
        size_mb=0,
        task="text-generation",
        source="groq",
        badge="Groq API",
        description="Meta LLaMA 3.3 70B via Groq. Primary Tier-1 planner. JSON mode "
                    "for structured output. ~180 tok/s on Groq hardware.",
        max_new_tokens=256,
    ),
    "groq-llama-3.1-8b": ModelEntry(
        model_id="llama-3.1-8b-instant",
        display_name="LLaMA 3.1 8B Instant",
        params_m=8_000,
        size_mb=0,
        task="text-generation",
        source="groq",
        badge="Groq API",
        description="Meta LLaMA 3.1 8B — fastest Groq model. ~750 tok/s. Good for "
                    "low-latency planning decisions.",
        max_new_tokens=256,
    ),
    "groq-mixtral-8x7b": ModelEntry(
        model_id="mixtral-8x7b-32768",
        display_name="Mixtral 8×7B",
        params_m=46_700,
        size_mb=0,
        task="text-generation",
        source="groq",
        badge="Groq API",
        description="Mistral MoE with 32K context. Strong multi-step reasoning and "
                    "long-context agent tasks.",
        max_new_tokens=512,
    ),
    "groq-gemma2-9b": ModelEntry(
        model_id="gemma2-9b-it",
        display_name="Gemma 2 9B-IT",
        params_m=9_000,
        size_mb=0,
        task="text-generation",
        source="groq",
        badge="Groq API",
        description="Google Gemma 2 9B instruction-tuned via Groq. Balanced performance "
                    "and speed for structured planning.",
        max_new_tokens=256,
    ),
}

# ─── Combined registry ─────────────────────────────────────────────────────────

ALL_MODELS: dict[str, ModelEntry] = {**LOCAL_MODELS, **GROQ_MODELS}


def get_model(key: str) -> ModelEntry:
    if key not in ALL_MODELS:
        raise KeyError(f"Unknown model key {key!r}. Available: {list(ALL_MODELS)}")
    return ALL_MODELS[key]


def registry_info() -> list[dict]:
    """Return metadata for all models without loading any weights."""
    groq_key_set = bool(os.environ.get("GROQ_API_KEY", "").strip())
    result = []
    for key, entry in ALL_MODELS.items():
        d = entry.to_dict()
        d["key"] = key
        if entry.source == "groq":
            d["available"] = groq_key_set
        result.append(d)
    return result
