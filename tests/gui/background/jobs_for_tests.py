# coding: utf-8

"""Jobs the process runner's tests send to a child interpreter.

They live in their own module because a spawned child re-imports the target by
name — a lambda or a test-local function cannot be pickled.
"""

from howl_editor.core.progress import ProgressReporter


def add(a: int, b: int, progress: ProgressReporter | None = None) -> int:
    return a + b


def boom(progress: ProgressReporter | None = None) -> None:
    raise ValueError("job went wrong")


def count_to(limit: int, progress: ProgressReporter | None = None) -> str:
    for done in range(limit):
        if progress is not None:
            progress.step(done, limit)

    return "finished"
