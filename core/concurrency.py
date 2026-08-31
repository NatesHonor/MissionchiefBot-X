"""Bounded fan-out helpers for browser data collection."""

from __future__ import annotations

import asyncio

from utils.pretty_print import display_error


async def split_mission_ids_among_threads(
    ids,
    contexts,
    num_threads,
    url,
    profile=None,
    state=None,
    progress=None,
):
    if not ids or not contexts or not num_threads:
        return {}
    workers = min(num_threads, len(contexts), len(ids))
    partitions = [ids[index::workers] for index in range(workers)]
    from .mission_parser import gather_mission_info

    results = await asyncio.gather(
        *(
            gather_mission_info(
                partition,
                contexts[index],
                index + 1,
                url,
                profile,
                state,
                progress,
            )
            for index, partition in enumerate(partitions)
            if partition
        ),
        return_exceptions=True,
    )
    merged = {}
    for index, result in enumerate(results, start=1):
        if isinstance(result, BaseException):
            display_error(
                f"Mission collection worker {index} failed: "
                f"{type(result).__name__}: {result}"
            )
            continue
        merged.update(result)
    return merged
