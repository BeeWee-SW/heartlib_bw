"""Progress reporting for a library that offers no callback hook.

``_forward`` drives its frame loop through a module-level ``tqdm`` symbol
(music_generation.py:8,316) and the vocoder does the same one level down
(heartcodec/models/flow_matching.py:4,143).  Swapping that symbol for the
duration of a run gives per-frame progress and a cancellation checkpoint
without copying any model logic.
"""

from __future__ import annotations

import math
from contextlib import contextmanager
from typing import Callable, Iterator

# Vocoder chunking constants, derived from detokenize(duration=29.76) at the
# codec's 12.5 Hz frame rate (heartcodec/modeling_heartcodec.py:61,74-75):
#   min_samples = int(29.76 * 12.5) = 372 ; hop = 372 // 93 * 80 = 320
_DECODE_HOP_FRAMES = 320


class JobCancelled(RuntimeError):
    """Raised inside the generation loop when the user cancels a job."""


def _make_wrapper(on_step: Callable[[int, int], None], should_cancel: Callable[[], bool] | None):
    def wrapper(iterable=None, *args, **kwargs):
        total = kwargs.get("total")
        if total is None and iterable is not None:
            try:
                total = len(iterable)
            except TypeError:
                total = None
        step = 0
        for item in iterable if iterable is not None else ():
            if should_cancel is not None and should_cancel():
                raise JobCancelled()
            yield item
            step += 1
            on_step(step, total or 0)

    return wrapper


@contextmanager
def track_generation(
    on_progress: Callable[[float, int, int], None],
    should_cancel: Callable[[], bool] | None = None,
) -> Iterator[None]:
    """Report the language model's frame loop as a 0..1 fraction.

    ``on_progress(fraction, frames_done, frames_total)`` is called once per
    generated frame.  The model stops early on EOS (music_generation.py:331),
    so the fraction is an upper bound on the work left, not a promise.
    """
    try:
        from heartlib.pipelines import music_generation
    except ImportError:
        yield
        return

    original = getattr(music_generation, "tqdm", None)
    if original is None:
        # Upstream renamed or dropped the symbol: run without a progress bar
        # rather than failing the generation.
        yield
        return

    def on_step(done: int, total: int) -> None:
        on_progress(min(done / total, 1.0) if total else 0.0, done, total)

    music_generation.tqdm = _make_wrapper(on_step, should_cancel)
    try:
        yield
    finally:
        music_generation.tqdm = original


@contextmanager
def track_decoding(
    frame_count: int,
    num_steps: int,
    on_progress: Callable[[float], None],
    should_cancel: Callable[[], bool] | None = None,
) -> Iterator[None]:
    """Report the vocoder's flow-matching loop as a 0..1 fraction.

    The chunk loop itself has no progress bar, so the inner per-step bar is
    counted and combined with an estimate of the chunk count.  If the estimate
    is off, the fraction is clamped rather than allowed to exceed 1.0.
    """
    try:
        from heartlib.heartcodec.models import flow_matching
    except ImportError:
        yield
        return

    original = getattr(flow_matching, "tqdm", None)
    if original is None:
        yield
        return

    chunks = max(1, math.ceil(max(frame_count, 1) / _DECODE_HOP_FRAMES))
    total_steps = max(1, chunks * max(num_steps, 1))
    state = {"done": 0}

    def on_step(done: int, total: int) -> None:
        state["done"] += 1
        on_progress(min(state["done"] / total_steps, 1.0))

    flow_matching.tqdm = _make_wrapper(on_step, should_cancel)
    try:
        yield
    finally:
        flow_matching.tqdm = original
