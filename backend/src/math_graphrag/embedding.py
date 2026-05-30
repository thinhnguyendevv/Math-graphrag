from __future__ import annotations

import os
from typing import Protocol


class EmbeddingModel(Protocol):
    def embed_query(self, text: str) -> list[float]: ...
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class HFEmbedding:
    def __init__(self, config: dict):
        from sentence_transformers import SentenceTransformer
        hf_cfg = config.get("embedding", {}).get("hf", {})
        self.model = SentenceTransformer(hf_cfg.get("model_name", "BAAI/bge-m3"))
        self.normalize = bool(hf_cfg.get("normalize_embeddings", True))

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=self.normalize).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=self.normalize, show_progress_bar=True).tolist()


class GeminiEmbedding:
    def __init__(self, config: dict):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        gem_cfg = config.get("embedding", {}).get("gemini", {})
        api_key = os.getenv(config.get("llm", {}).get("gemini", {}).get("api_key_env", "GOOGLE_API_KEY"))
        self.model = GoogleGenerativeAIEmbeddings(
            model=gem_cfg.get("model", "models/text-embedding-004"),
            google_api_key=api_key,
        )

    def embed_query(self, text: str) -> list[float]:
        return self.model.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.embed_documents(texts)


def get_embedding_model(config: dict):
    provider = config.get("embedding", {}).get("provider", "hf")
    if provider == "hf":
        return HFEmbedding(config)
    if provider == "gemini":
        return GeminiEmbedding(config)
    raise ValueError(f"Unsupported embedding provider: {provider}")
