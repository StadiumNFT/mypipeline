"""Model provider adapters for the post-processing step."""
from .provider_gpt5_vision import analyze_card as analyze_with_gpt5

__all__ = ["analyze_with_gpt5"]
