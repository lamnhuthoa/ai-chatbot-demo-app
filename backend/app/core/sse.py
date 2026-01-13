from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, Optional, Callable, Iterator, AsyncGenerator
import contextlib


def format_sse_event(event_name: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
    """
    SSE format:
      id: <optional>
      event: <name>
      data: <json string>

    Each event must end with a blank line.
    """
    json_payload = json.dumps(data, ensure_ascii=False)

    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_name}")
    lines.append(f"data: {json_payload}")
    return "\n".join(lines) + "\n\n"


def format_sse_comment(comment: str = "heartbeat") -> str:
  """Build an SSE comment line. Proxies typically pass these and keep connections alive."""
  return f": {comment}\n\n"


async def stream_sync_iter_as_sse(
  iter_fn: Callable[[], Iterator[str]],
  *,
  request,
  request_id: str,
  heartbeat_interval: float = 15.0,
) -> AsyncGenerator[str, None]:
  """Adapt a blocking/sync iterator of text chunks into an async SSE stream with heartbeats.

  - Produces a 'start' event first
  - Then 'content' events per chunk
  - Emits periodic SSE comments as heartbeats
  - Finishes with a 'done' event or an 'error' event on failure
  """
  queue: asyncio.Queue[Optional[str]] = asyncio.Queue(maxsize=100)
  error_message: Optional[str] = None

  async def produce() -> None:
    nonlocal error_message
    loop = asyncio.get_running_loop()

    def run() -> None:
      nonlocal error_message
      try:
        for piece in iter_fn():
          # Block if queue is full; backpressure
          asyncio.run_coroutine_threadsafe(queue.put(piece), loop).result()
      except Exception as exc:  # noqa: BLE001 - capture and report downstream
        error_message = str(exc)
      finally:
        asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

    await asyncio.to_thread(run)

  producer_task = asyncio.create_task(produce())

  # Start event
  yield format_sse_event("start", {"requestId": request_id})
  # Inform client that the bot is thinking
  yield format_sse_event("BOT_THINKING", {"requestId": request_id, "content": "Thinking..."})

  full_text: list[str] = []
  try:
    while True:
      if await request.is_disconnected():  # type: ignore[attr-defined]
        break
      try:
        item = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
      except asyncio.TimeoutError:
        # Heartbeat comment to keep connections alive through proxies
        yield format_sse_comment()
        continue

      if item is None:
        break

      full_text.append(item)
      yield format_sse_event("BOT_Response", {"requestId": request_id, "content": item})

  finally:
    # Ensure producer completes
    with contextlib.suppress(Exception):  # type: ignore[name-defined]
      await producer_task

  if error_message:
    yield format_sse_event("error", {"requestId": request_id, "message": error_message})
  else:
    yield format_sse_event("done", {"requestId": request_id, "content": "".join(full_text)})

