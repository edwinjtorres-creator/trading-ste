"""
RAG sobre documentación: *Pinecone/Milvus + embeddings* se cablearán sin importar
pesados en el arranque del *kernel*. Por ahora, un *stub* explícito.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class RAGIndexStub:
    _docs: list[dict[str, Any]] = field(default_factory=list)

    def add_texts(self, parts: Sequence[str], meta: Sequence[dict] | None = None) -> None:
        m = list(meta) if meta is not None else [{}] * len(parts)
        for t, d in zip(parts, m, strict=True):
            self._docs.append({"text": t, "meta": d})

    def query(self, _q: str, k: int = 3) -> list[dict[str, Any]]:
        return [dict(d) for d in self._docs[:k]]


@dataclass
class VectorStorePlanned:
    """
    *Placeholder* con lo que faltaría: cliente Milvus o Pinecone + modelo de
    *embedding* (SentenceTransformers, etc.); añademe cuando tengas credenciales.
    """

    endpoint: str = "local://unconfigured"
