"""
Retry Strategy Pattern

Provides unified retry logic with exponential backoff across the application.
Consolidates retry patterns from fan_control, command_executor, and dependency_installer.

DESIGN PATTERN: Strategy Pattern
- Encapsulates retry algorithm
- Allows different retry configurations
- Reduces code duplication
"""

import time
from typing import Callable, TypeVar, Optional, Any, Union, Sequence
from .logger import logger
from .constants import RETRY_CONFIG

T = TypeVar('T')


class RetryStrategy:
    """
    Unified retry strategy with exponential backoff.
    
    Consolidates retry patterns used across multiple modules:
    - fan_control.py (hardware retries)
    - command_executor.py (subprocess retries)
    - dependency_installer.py (package installation retries)
    
    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        exponential_base: Multiplier for exponential backoff (default: 2.0)
        
    Examples:
        >>> strategy = RetryStrategy(max_retries=3, base_delay=0.1)
        >>> result = strategy.execute_with_retry(
        ...     lambda: risky_operation(),
        ...     predicate=lambda x: x is not None
        ... )
    """
    
    def __init__(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        exponential_base: float = 2.0,
    ):
        """
        Initialize retry strategy.
        
        Args:
            max_retries: Max attempts. If None, uses RETRY_CONFIG["max_retries"]
            base_delay: Initial delay in seconds. If None, uses RETRY_CONFIG["base_delay"]
            exponential_base: Multiplier for exponential backoff (default: 2.0)
        """
        self.max_retries = max_retries or RETRY_CONFIG.get("max_retries", 3)
        self.base_delay = base_delay or RETRY_CONFIG.get("base_delay", 0.1)
        self.exponential_base = exponential_base
        
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        predicate: Optional[Callable[[T], bool]] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        on_failure: Optional[Callable[[int, Exception], None]] = None,
        **kwargs
    ) -> T:
        """
        Execute function with exponential backoff retry.
        
        Args:
            func: Callable to execute
            *args: Positional arguments to func
            predicate: Optional function to check if result is successful.
                      If None, any non-exception result is considered success.
                      Example: predicate=lambda x: x is not None
            on_retry: Optional callback when retry occurs: on_retry(attempt, error)
            on_failure: Optional callback when all retries exhausted: on_failure(attempt, error)
            **kwargs: Keyword arguments to func
            
        Returns:
            Result of successful func execution
            
        Raises:
            Exception: Final exception if all retries fail
            
        Examples:
            >>> strategy = RetryStrategy(max_retries=3)
            >>> result = strategy.execute_with_retry(
            ...     risky_func,
            ...     arg1,
            ...     key1=value1,
            ...     predicate=lambda x: x != None
            ... )
        """
        last_error: Union[Exception, str] = "Unknown error"
        last_result = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # Check if result satisfies predicate
                if predicate is None or predicate(result):
                    return result
                    
                # Predicate failed, treat as error
                last_result = result
                last_error = f"Predicate failed for result: {result}"
                
                if attempt < self.max_retries:
                    wait_time = self._calculate_backoff(attempt - 1)
                    logger.debug(
                        f"Retry {attempt}/{self.max_retries}: "
                        f"predicate failed, waiting {wait_time:.2f}s"
                    )
                    if on_retry:
                        on_retry(attempt, Exception(last_error))
                    time.sleep(wait_time)
                    
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    wait_time = self._calculate_backoff(attempt - 1)
                    logger.debug(
                        f"Retry {attempt}/{self.max_retries}: {type(e).__name__}: {e}, "
                        f"waiting {wait_time:.2f}s"
                    )
                    if on_retry:
                        on_retry(attempt, e)
                    time.sleep(wait_time)
        
        # All retries exhausted
        if on_failure:
            on_failure(self.max_retries, 
                      last_error if isinstance(last_error, Exception) 
                      else Exception(last_error))
        
        if isinstance(last_error, Exception):
            raise last_error
        else:
            raise Exception(str(last_error))
    
    def execute_with_retry_silent(
        self,
        func: Callable[..., T],
        default: T,
        *args,
        predicate: Optional[Callable[[T], bool]] = None,
        **kwargs
    ) -> T:
        """
        Execute function with retry, returning default on failure.
        
        Useful when operation failures are non-fatal.
        
        Args:
            func: Callable to execute
            default: Value to return if all retries fail
            *args: Positional arguments to func
            predicate: Optional predicate to check success
            **kwargs: Keyword arguments to func
            
        Returns:
            Result of func if successful, else default
            
        Examples:
            >>> strategy = RetryStrategy()
            >>> result = strategy.execute_with_retry_silent(
            ...     read_file,
            ...     default="default content",
            ...     filename="config.json"
            ... )
        """
        try:
            return self.execute_with_retry(func, *args, predicate=predicate, **kwargs)
        except Exception as e:
            logger.warning(f"Retry exhausted, returning default: {e}")
            return default
    
    def _calculate_backoff(self, attempt_index: int) -> float:
        """
        Calculate backoff delay for exponential retry.
        
        Args:
            attempt_index: 0-based attempt index
            
        Returns:
            Delay in seconds
            
        Examples:
            >>> strategy = RetryStrategy(base_delay=0.1, exponential_base=2.0)
            >>> strategy._calculate_backoff(0)  # 0.1 * 2^0 = 0.1
            0.1
            >>> strategy._calculate_backoff(1)  # 0.1 * 2^1 = 0.2
            0.2
            >>> strategy._calculate_backoff(2)  # 0.1 * 2^2 = 0.4
            0.4
        """
        return self.base_delay * (self.exponential_base ** attempt_index)


# Pre-configured retry strategies for common use cases
AGGRESSIVE_RETRY = RetryStrategy(max_retries=5, base_delay=0.05)
NORMAL_RETRY = RetryStrategy(max_retries=3, base_delay=0.1)
GENTLE_RETRY = RetryStrategy(max_retries=2, base_delay=0.5)
