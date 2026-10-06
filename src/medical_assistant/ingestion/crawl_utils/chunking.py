"""Token-aware text chunking shared by the Vinmec RAG builders."""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken


class _FallbackEncoding:
    """Offline approximation used when tiktoken vocabulary is unavailable."""

    @staticmethod
    def encode(text: str) -> list[str]:
        return text.split()

    @staticmethod
    def decode(tokens: list[str]) -> str:
        return " ".join(tokens)


@dataclass(frozen=True)
class TokenChunk:
    """One decoded token window and its position within the parent document."""

    text: str
    token_count: int
    index: int
    count: int


class TokenChunker:
    """Split a body into overlapping token windows while repeating its context."""

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 80,
        encoding_name: str = "cl100k_base",
    ) -> None:
        if chunk_size < 64:
            raise ValueError("chunk_size must be at least 64 tokens")
        if overlap < 0:
            raise ValueError("overlap cannot be negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding_name = encoding_name
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.encoding = _FallbackEncoding()

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def split(self, body: str, *, prefix: str = "", suffix: str = "") -> list[TokenChunk]:
        """Return chunks whose complete rendered text fits ``chunk_size`` tokens."""
        prefix_text = f"{prefix}\n\n" if prefix else ""
        suffix_text = f"\n\n{suffix}" if suffix else ""
        context_tokens = self.count_tokens(prefix_text) + self.count_tokens(suffix_text)
        capacity = self.chunk_size - context_tokens
        if capacity <= self.overlap:
            raise ValueError("chunk_size is too small for the repeated context and requested overlap")

        body_tokens = self.encoding.encode(body.strip())
        if not body_tokens:
            return []

        windows: list[list[int]] = []
        start = 0
        while start < len(body_tokens):
            end = min(start + capacity, len(body_tokens))
            window = body_tokens[start:end]
            rendered = f"{prefix_text}{self.encoding.decode(window)}{suffix_text}"
            while window and self.count_tokens(rendered) > self.chunk_size:
                end -= 1
                window = body_tokens[start:end]
                rendered = f"{prefix_text}{self.encoding.decode(window)}{suffix_text}"
            if not window or (end < len(body_tokens) and end - start <= self.overlap):
                raise ValueError("chunk_size leaves too little room for content after tokenization")
            windows.append(window)
            if end == len(body_tokens):
                break
            start = end - self.overlap

        count = len(windows)
        chunks: list[TokenChunk] = []
        for index, tokens in enumerate(windows, start=1):
            text = f"{prefix_text}{self.encoding.decode(tokens)}{suffix_text}"
            chunks.append(
                TokenChunk(
                    text=text,
                    token_count=self.count_tokens(text),
                    index=index,
                    count=count,
                )
            )
        return chunks
