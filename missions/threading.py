import asyncio
from .mission_parser import gather_mission_info

async def split_mission_ids_among_threads(ids, contexts, n):
    for ctx in contexts:
        if not ctx.pages:
            await ctx.new_page()
    tasks = [
        gather_mission_info(ids[i::n], contexts[i], i + 1)
        for i in range(min(n, len(contexts)))
    ]
    results = await asyncio.gather(*tasks)
    return {k: v for r in results for k, v in r.items()}
