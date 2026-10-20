"""Small Playwright helpers shared by browser workflows."""


async def ensure_page(context):
    if context.pages:
        return context.pages[0]
    return await context.new_page()
