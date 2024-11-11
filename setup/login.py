from utils.pretty_print import display_info, display_error

async def login_single(username, password, headless, thread_id, delay, playwright):
    display_info(f"Starting login for browser: {thread_id}")
    browser = None
    try:
        browser = await playwright.chromium.launch(headless=headless, devtools=False)
        page = await browser.new_page()

        await page.goto("https://www.missionchief.com/users/sign_in")
        await page.wait_for_selector("form#new_user")
        await page.fill('input[name="user[email]"]', username)
        await page.fill('input[name="user[password]"]', password)
        await page.click('input[type="submit"]')
        await page.wait_for_load_state("networkidle")

        error_message = page.locator('text=Invalid email or password')
        if await error_message.is_visible(timeout=5000):
            return "Failure", f"Thread {thread_id}: Invalid email or password", browser

        return "Success", thread_id, browser

    except Exception as e:
        display_error(f"Thread {thread_id} encountered an error: {e}")
        if browser:
            await browser.close()
        return "Failure", f"Thread {thread_id} failed due to an unexpected error: {e}", None
