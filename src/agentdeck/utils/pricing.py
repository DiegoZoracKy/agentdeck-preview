"""Pricing utilities for LLM cost calculations."""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

# Cache the loaded pricing data
_pricing_data: Optional[Dict] = None


def _validate_pricing_structure(data: Dict) -> None:
    """
    Validate pricing.yaml structure to catch typos and malformed data.

    Args:
        data: The loaded pricing data dictionary

    Raises:
        ValueError: If structure is invalid
    """
    if not data:
        return  # Empty dict is valid (will trigger warnings elsewhere)

    for provider, models in data.items():
        if provider == "metadata":
            continue  # Skip metadata section

        if not isinstance(models, dict):
            raise ValueError(
                f"Invalid pricing for provider '{provider}': "
                f"expected dict, got {type(models).__name__}"
            )

        for model, model_data in models.items():
            if model.startswith("_"):  # Skip special keys like _default
                continue

            if not isinstance(model_data, dict):
                raise ValueError(
                    f"Invalid pricing for {provider}/{model}: "
                    f"expected dict, got {type(model_data).__name__}"
                )

            required_keys = ["input_cost_per_million", "output_cost_per_million"]
            for key in required_keys:
                if key not in model_data:
                    raise ValueError(f"Missing '{key}' for {provider}/{model}")

                value = model_data[key]
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Invalid {key} for {provider}/{model}: "
                        f"expected number, got {type(value).__name__} (value: {value})"
                    )

                if value < 0:
                    raise ValueError(f"Negative cost for {provider}/{model}: {key}={value}")


def load_pricing_data() -> Dict:
    """
    Load pricing data from YAML file.

    Returns:
        Dict containing pricing data, or empty dict if file not found/invalid

    Note:
        Validates YAML structure on load. Invalid structure raises ValueError
        and prevents caching of bad data.
    """
    global _pricing_data

    if _pricing_data is not None:
        return _pricing_data

    # Find the pricing.yaml file
    current_dir = Path(__file__).parent.parent
    pricing_file = current_dir / "config" / "pricing.yaml"

    if not pricing_file.exists():
        # Return empty dict if file not found - costs will be zero
        logging.warning(f"pricing.yaml not found at {pricing_file} - costs will be zero")
        return {}

    try:
        with open(pricing_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

            # Validate structure before caching
            _validate_pricing_structure(data)

            _pricing_data = data
            return data
    except ValueError as e:
        # Validation failed - don't cache bad data
        logging.error(f"pricing.yaml validation failed: {e}")
        raise
    except Exception as e:
        logging.error(f"Could not load pricing.yaml: {e} - costs will be zero")
        return {}


def get_model_pricing(
    provider: str, model: str, allow_missing: bool = False
) -> Tuple[float, float]:
    """
    Get pricing for a specific model.

    Args:
        provider: Provider name (e.g., 'openai', 'anthropic')
        model: Model name (e.g., 'gpt-4o', 'claude-3-opus')
        allow_missing: If False (default), raises ValueError for unknown provider/model.
                      If True, returns (0.0, 0.0) with a warning.

    Returns:
        Tuple of (input_cost_per_million, output_cost_per_million)

    Raises:
        ValueError: If provider/model not found and allow_missing=False
    """
    pricing_data = load_pricing_data()

    # Check if pricing data was loaded successfully
    if not pricing_data:
        if allow_missing:
            logging.warning(
                f"Pricing data not loaded. Returning $0.00 for {provider}/{model}. "
                "Set allow_missing=False to raise errors instead."
            )
            return (0.0, 0.0)
        else:
            raise ValueError(
                f"Pricing data not loaded (pricing.yaml missing or invalid). "
                f"Cannot determine cost for {provider}/{model}."
            )

    # Get provider pricing
    provider_pricing = pricing_data.get(provider, {})

    # Try exact model match first
    if model in provider_pricing:
        model_data = provider_pricing[model]
        return (
            model_data.get("input_cost_per_million", 0.0),
            model_data.get("output_cost_per_million", 0.0),
        )

    # Use provider's default if available
    if "_default" in provider_pricing:
        default_data = provider_pricing["_default"]
        logging.info(
            f"Using default pricing for {provider}/{model} "
            f"(${default_data.get('input_cost_per_million', 0.0)}/M input, "
            f"${default_data.get('output_cost_per_million', 0.0)}/M output)"
        )
        return (
            default_data.get("input_cost_per_million", 0.0),
            default_data.get("output_cost_per_million", 0.0),
        )

    # No pricing found
    if allow_missing:
        logging.warning(
            f"No pricing data found for {provider}/{model}. Returning $0.00. "
            "This likely indicates a typo in provider or model name. "
            f"Available providers: {list(pricing_data.keys())}"
        )
        return (0.0, 0.0)
    else:
        available_providers = [k for k in pricing_data.keys() if k != "metadata"]
        available_models = list(provider_pricing.keys()) if provider_pricing else []
        raise ValueError(
            f"No pricing found for {provider}/{model}. "
            f"Available providers: {available_providers}. "
            f"Available models for '{provider}': {available_models}. "
            "Set allow_missing=True to return $0.00 instead of raising."
        )


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate the cost for an API call.

    Args:
        provider: Provider name
        model: Model name
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens

    Returns:
        Total cost in USD

    Note:
        For backward compatibility, this function catches ValueError from get_model_pricing()
        and returns $0.00, but logs an ERROR every time. This ensures researchers notice
        configuration mistakes (typos in provider/model names).

        For stricter behavior, call get_model_pricing() directly with allow_missing=False.
    """
    try:
        input_cost_per_million, output_cost_per_million = get_model_pricing(
            provider, model, allow_missing=False
        )
    except ValueError as e:
        # Log ERROR every time (not cached, so user sees it repeatedly)
        logging.error(
            f"Cost calculation failed: {e}. Returning $0.00. "
            "This error will repeat for every API call until fixed."
        )
        input_cost_per_million, output_cost_per_million = 0.0, 0.0

    input_cost = (prompt_tokens / 1_000_000) * input_cost_per_million
    output_cost = (completion_tokens / 1_000_000) * output_cost_per_million

    return input_cost + output_cost


def reload_pricing():
    """Force reload of pricing data from file."""
    global _pricing_data
    _pricing_data = None
    return load_pricing_data()
