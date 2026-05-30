from __future__ import annotations

import os
import re
from typing import Protocol


class SimpleLLM(Protocol):
    def invoke(self, prompt: str) -> str: ...


class LLMQuotaError(RuntimeError):
    """Raised when the remote LLM provider reports quota/rate exhaustion."""


def _extract_retry_seconds(message: str) -> str | None:
    patterns = [
        r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s",
        r"retry in\s+([0-9.]+)s",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return str(int(float(match.group(1))))
    return None


class GeminiLLM:
    def __init__(self, config: dict):
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm_cfg = config.get("llm", {})
        gem_cfg = llm_cfg.get("gemini", {})
        api_key = os.getenv(gem_cfg.get("api_key_env", "GOOGLE_API_KEY"))
        if not api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY. Please set it in .env")
        self.model = ChatGoogleGenerativeAI(
            model=gem_cfg.get("model", "gemini-1.5-flash"),
            temperature=float(llm_cfg.get("temperature", 0.1)),
            google_api_key=api_key,
        )

    def invoke(self, prompt: str) -> str:
        try:
            res = self.model.invoke(prompt)
            return getattr(res, "content", str(res))
        except Exception as exc:
            message = str(exc)
            quota_markers = (
                "RESOURCE_EXHAUSTED",
                "429",
                "quota",
                "rate limit",
                "GenerateRequestsPerDayPerProjectPerModel",
            )
            if any(marker.lower() in message.lower() for marker in quota_markers):
                retry_seconds = _extract_retry_seconds(message)
                retry_text = f" Thử lại sau khoảng {retry_seconds} giây." if retry_seconds else ""
                raise LLMQuotaError(
                    "Gemini API đã hết quota hoặc bị giới hạn tốc độ."
                    f"{retry_text} Nếu lỗi vẫn lặp lại, hãy đổi API key, bật billing, đổi model, "
                    "hoặc giảm số lần gọi LLM."
                ) from exc
            raise


class HuggingFaceLocalLLM:
    def __init__(self, config: dict):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        llm_cfg = config.get("llm", {})
        hf_cfg = llm_cfg.get("hf", {})
        model_name = hf_cfg.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct")
        device = hf_cfg.get("device", "auto")
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            device_map=device,
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=int(hf_cfg.get("max_new_tokens", 1024)),
            do_sample=False,
        )

    def invoke(self, prompt: str) -> str:
        out = self.pipe(prompt)[0]["generated_text"]
        if out.startswith(prompt):
            out = out[len(prompt):]
        return out.strip()


def get_llm(config: dict):
    llm_cfg = config.get("llm", {})
    provider_env = llm_cfg.get("provider_env", "LLM_PROVIDER")
    provider = os.getenv(provider_env, llm_cfg.get("provider", "gemini"))
    if provider == "gemini":
        return GeminiLLM(config)
    if provider == "hf":
        return HuggingFaceLocalLLM(config)
    raise ValueError(f"Unsupported LLM provider: {provider}")
