from playwright.async_api import async_playwright, Page
import asyncio


async def handle_transport_requests(page: Page):
    await page.wait_for_load_state('networkidle')
    transport_requests = await page.query_selector_all('ul#radio_messages_important li')
    if transport_requests:
        print(f"Transporting Prisoners and Patients for {len(transport_requests)} vehicle(s)")
        vehicle_urls = []
        for request in transport_requests:
            vehicle_id = await request.get_attribute('vehicle_id')
            if vehicle_id:
                vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
                vehicle_urls.append(vehicle_url)
        for vehicle_url in vehicle_urls:
            print(f"Navigating to vehicle URL: {vehicle_url}")
            await page.goto(vehicle_url)
            await page.wait_for_load_state('networkidle')
            hospitals = await page.query_selector_all('table#own-hospitals tbody tr')
            selected_hospital = None
            for hospital in hospitals:
                transport_button = await hospital.query_selector('a.btn.btn-success')
                if transport_button:
                    transport_text = await transport_button.inner_text()
                    if "Transport Patient" in transport_text:
                        selected_hospital = hospital
                        break
            if selected_hospital:
                print(f"Transporting to selected hospital.")
                transport_button = await selected_hospital.query_selector('a.btn.btn-success')
                await transport_button.click()
                await page.wait_for_load_state('networkidle')
            else:
                alliance_hospitals = await page.query_selector_all('table#alliance-hospitals tbody tr')
                for alliance_hospital in alliance_hospitals:
                    transport_button = await alliance_hospital.query_selector('a.btn.btn-success')
                    if transport_button:
                        print(f"Transporting to alliance hospital.")
                        await transport_button.click()
                        await page.wait_for_load_state('networkidle')
                        break
                else:
                    leave_button = await page.query_selector('a#leave_without_transport_no_compensation')
                    if leave_button:
                        print(f"No hospitals available. Leaving the patient at the scene.")
                        await leave_button.click()
                        await page.wait_for_load_state('networkidle')


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set headless=False for debugging
        page = await browser.new_page()
        await page.goto("https://www.missionchief.com")

        # Call the function to handle transport requests
        await handle_transport_requests(page)

        await browser.close()


# Run the script
asyncio.run(run())
