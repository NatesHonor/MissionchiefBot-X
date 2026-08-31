"""Bounded fan-out helpers for browser data collection."""

from __future__ import annotations

import asyncio


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
        )
    )
    merged = {}
    for result in results:
        merged.update(result)
    return merged
