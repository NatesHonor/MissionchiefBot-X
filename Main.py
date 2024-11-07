from setup.login import login
import asyncio


async def main():
    status, result, browsers = await login()

    if status == "Failure":
        print("Login failed. Errors:")
        print("\n".join(result))
        return

    print(f"All drivers logged in successfully. Threads: {', '.join(map(str, result))}")

    thread_id = result[0]
    browser = browsers[0]
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.missionchief.com/leitstellenansicht")
    red_buttons = await page.locator('a.btn-danger').all()
    for button in red_buttons:
        await button.click()

    print(f"Successfully navigated to Leitstellenansicht for thread {thread_id}")


if __name__ == "__main__":
    asyncio.run(main())
