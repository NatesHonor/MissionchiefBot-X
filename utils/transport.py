async def handle_transport_requests(browser):
    page = browser.contexts[0].pages[0]
    await page.goto("https://www.missionchief.com")
    await page.wait_for_load_state('networkidle')

    transport_requests = await page.query_selector_all('ul#radio_messages_important li')
    print(f"Found {len(transport_requests)} transport requests")

    if transport_requests:
        vehicle_urls = []
        for request in transport_requests:
            vehicle_id_element = await request.query_selector('img')
            if vehicle_id_element:
                vehicle_id = await vehicle_id_element.get_attribute('vehicle_id')
                print(f"Found vehicle with ID: {vehicle_id}")
                vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
                vehicle_urls.append(vehicle_url)

        for vehicle_url in vehicle_urls:
            await page.goto(vehicle_url)
            await page.wait_for_load_state('networkidle')

            hospitals_table = await page.query_selector('table#own-hospitals')

            if hospitals_table:
                hospitals = await page.query_selector_all('table#own-hospitals tbody tr')
                print(f"Found {len(hospitals)} hospitals")

                smallest_distance = float('inf')
                transport_button_to_click = None

                for hospital in hospitals:
                    distance_element = await hospital.query_selector('td:nth-child(2)')
                    if distance_element:
                        distance_text = await distance_element.inner_text()
                        try:
                            distance_value = float(distance_text.split()[0])
                        except ValueError:
                            continue

                        transport_button = await hospital.query_selector('a.btn.btn-success')

                        if distance_value < smallest_distance and transport_button:
                            smallest_distance = distance_value
                            transport_button_to_click = transport_button

                if transport_button_to_click:
                    await transport_button_to_click.click()
                    await page.wait_for_load_state('networkidle')

            else:
                patrol_buttons = await page.query_selector_all('a.btn.btn-success')
                print(f"Found {len(patrol_buttons)} patrol transport buttons")

                smallest_distance = float('inf')
                transport_button_to_click = None

                for button in patrol_buttons:
                    button_text = await button.inner_text()

                    distance_start = button_text.find("Distance: ")
                    if distance_start != -1:
                        distance_text = button_text[distance_start + len("Distance: "):]
                        try:
                            distance_value = float(distance_text.split()[0])
                        except ValueError:
                            continue

                        if distance_value < smallest_distance:
                            smallest_distance = distance_value
                            transport_button_to_click = button

                if transport_button_to_click:
                    await transport_button_to_click.click()
                    await page.wait_for_load_state('networkidle')
                else:
                    release_button = await page.query_selector('a.btn.btn-xs.btn-danger')
                    if release_button:
                        await release_button.click()
                        await page.wait_for_load_state('networkidle')
                        print("No green buttons left, clicked 'Release Prisoners' button.")
                    else:
                        print("No transport buttons or 'Release Prisoners' button found.")

        print("Handled transport requests for all vehicles.")
