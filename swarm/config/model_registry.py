"""Model context window registry for budget computation.

Provides context window sizes for known models, enabling fraction-based
budget computation.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ModelSpec:
    """Specification for a model's context window."""
    model_id: str
    context_tokens: int
    description: str = ""

    @property
    def context_chars(self) -> int:
        """Approximate character count (4 chars per token)."""
        return self.context_tokens * 4


@dataclass
class BudgetFractions:
    """Fraction-based budget configuration."""
    history_total: float = 0.25      # 25% of window
    history_recent: float = 0.075    # 7.5% for recent step
    history_older: float = 0.025     # 2.5% per older step


# Built-in model specs
BUILTIN_MODELS: Dict[str, ModelSpec] = {
    "claude-sonnet-4": ModelSpec("claude-sonnet-4", 200000, "Claude Sonnet 4"),
    "claude-opus-4-5": ModelSpec("claude-opus-4-5", 200000, "Claude Opus 4.5"),
    "gemini-1.5-flash": ModelSpec("gemini-1.5-flash", 1048576, "Gemini 1.5 Flash 1M"),
    "gemini-1.5-pro": ModelSpec("gemini-1.5-pro", 2097152, "Gemini 1.5 Pro 2M"),
    "gemini-2.0-flash": ModelSpec("gemini-2.0-flash", 128000, "Gemini 2.0 Flash 128k"),
}

DEFAULT_FRACTIONS = BudgetFractions()


def get_model_spec(model_id: str) -> Optional[ModelSpec]:
    """Get model spec by ID."""
    return BUILTIN_MODELS.get(model_id)


def get_model_context_tokens(model_id: str, default: int = 200000) -> int:
    """Get context window size in tokens for a model."""
    model = get_model_spec(model_id)
    return model.context_tokens if model else default


def compute_model_budgets(
    model_id: str,
    fractions: Optional[BudgetFractions] = None,
) -> Dict[str, int]:
    """Compute budget values for a model ID using fractions.

    Args:
        model_id: Model identifier
        fractions: Optional custom fractions, defaults to DEFAULT_FRACTIONS

    Returns:
        Dict with context_budget_chars, history_max_recent_chars,
        history_max_older_chars computed from model window.
    """
    model = get_model_spec(model_id)
    if not model:
        # Fallback to hardcoded defaults for unknown models
        return {
            "context_budget_chars": 200000,
            "history_max_recent_chars": 60000,
            "history_max_older_chars": 10000,
        }

    f = fractions or DEFAULT_FRACTIONS
    context_chars = model.context_chars

    return {
        "context_budget_chars": int(context_chars * f.history_total),
        "history_max_recent_chars": int(context_chars * f.history_recent),
        "history_max_older_chars": int(context_chars * f.history_older),
    }


def list_known_models() -> Dict[str, ModelSpec]:
    """Return all known model specs."""
    return dict(BUILTIN_MODELS)
