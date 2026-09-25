from .embeddings import MiniLMEmbeddings
from .index import LocalEmbeddingIndex, SearchResult

__all__ = [
    "MiniLMEmbeddings", "LocalEmbeddingIndex", "SearchResult", "build_agent",
    "run_agent_question", "build_llm", "AnswerResult", "answer_question",
]


def __getattr__(name):
    if name in {"build_agent", "run_agent_question"}:
        from . import agent

        return getattr(agent, name)
    if name == "build_llm":
        from . import llm

        return llm.build_llm
    if name in {"AnswerResult", "answer_question"}:
        from . import qa

        return getattr(qa, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
