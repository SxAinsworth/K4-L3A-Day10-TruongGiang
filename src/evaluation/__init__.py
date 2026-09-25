from .testset import BenchmarkTestSet, build_test_set, load_or_create_test_set

__all__ = [
    "build_test_set",
    "load_or_create_test_set",
    "BenchmarkTestSet",
    "EvaluationBundle",
    "JudgeVerdict",
    "evaluate_pipeline",
]


def __getattr__(name):
    """Avoid loading the optional PyArrow/Ragas stack for test-set creation."""
    if name in {"EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"}:
        from . import metrics

        return getattr(metrics, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
