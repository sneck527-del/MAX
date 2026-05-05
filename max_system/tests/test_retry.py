"""测试重试工具"""

import pytest
from max_system.utils.retry import retry_with_backoff, async_retry


class TestRetryWithBackoff:
    """retry_with_backoff测试"""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_with_backoff(succeed, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temp error")
            return "finally"

        result = await retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "finally"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        async def always_fail():
            raise RuntimeError("always")

        with pytest.raises(RuntimeError, match="always"):
            await retry_with_backoff(always_fail, max_retries=2, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_only_specific_exceptions_retried(self):
        call_count = 0

        async def type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("bad type")

        with pytest.raises(TypeError):
            # Only retry ValueError, not TypeError
            await retry_with_backoff(type_error, max_retries=3, base_delay=0.01, exceptions=(ValueError,))

        assert call_count == 1


class TestAsyncRetryDecorator:
    """async_retry装饰器测试"""

    def test_decorator_preserves_metadata(self):
        @async_retry(max_retries=3)
        async def my_func(x):
            """My docstring"""
            return x

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "My docstring"

    @pytest.mark.asyncio
    async def test_decorated_function_works(self):
        call_count = 0

        @async_retry(max_retries=3, base_delay=0.01)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("net")
            return "done"

        result = await flaky()
        assert result == "done"
        assert call_count == 2
