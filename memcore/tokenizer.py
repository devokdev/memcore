"""Token counting utilities supporting accurate tiktoken encoding with fallback estimation."""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

_ENCODER = None
_TIKTOKEN_AVAILABLE = False

try:
    import tiktoken
    try:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
        _TIKTOKEN_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Failed to load tiktoken encoding cl100k_base: {e}")
except ImportError:
    pass


def count_tokens(text: str) -> Tuple[int, bool]:
    """Counts tokens in the provided text.
    
    Returns:
        (token_count, is_estimated)
    """
    if not text:
        return 0, False
        
    if _TIKTOKEN_AVAILABLE and _ENCODER is not None:
        try:
            return len(_ENCODER.encode(text)), False
        except Exception as e:
            logger.debug(f"Tiktoken encoding failed: {e}, falling back to estimation")
            
    # Fallback heuristic: 1 token ~= 4 characters for English / code
    # Max with 1 if text is non-empty
    est = max(1, (len(text) + 3) // 4)
    return est, True
