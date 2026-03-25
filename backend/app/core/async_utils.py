import asyncio
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


async def run_sync(fn: Callable[..., T], *args) -> T:
    """Run a blocking function in the default thread-pool executor."""
    return await asyncio.get_running_loop().run_in_executor(None, fn, *args)
