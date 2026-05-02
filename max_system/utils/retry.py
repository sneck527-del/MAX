"""指数退避重试工具"""

import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    fn: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
) -> T:
    """带指数退避的异步重试"""
    for attempt in range(max_retries):
        try:
            return await fn()
        except exceptions as e:
            if attempt == max_retries - 1:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"第{attempt + 1}次重试失败: {e}，{delay:.1f}秒后重试")
            await asyncio.sleep(delay)


def async_retry(max_retries: int = 3, base_delay: float = 1.0, exceptions: tuple = (Exception,)):
    """异步重试装饰器"""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                lambda: fn(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                exceptions=exceptions,
            )
        return wrapper
    return decorator
