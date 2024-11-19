async def handle_transport_requests(browser):
    page = browser.contexts[0].pages[0]
    await page.goto("https://www.missionchief.com")
    await page.wait_for_load_state('networkidle')

    cell_selection = await page.query_selector('h2:has-text("Cell Selection")')
    if cell_selection:
        to_mission_place_button = await page.query_selector('a#btn_to_mission_place')
        if to_mission_place_button:
            await to_mission_place_button.click()
            await page.wait_for_load_state('networkidle')

            prisoners_element = await page.query_selector('h4#h2_prisoners')
            if prisoners_element:
                prisoner_text = await prisoners_element.inner_text()
                total_prisoners = int(prisoner_text.split()[0])
                print(f"Total prisoners: {total_prisoners}")

                mission_vehicle_table = await page.query_selector('table#mission_vehicle_at_mission tbody')
                vehicles = await mission_vehicle_table.query_selector_all('tr')
                prisoner_van = None
                available_vehicles = []

                for vehicle in vehicles:
                    vehicle_type = await vehicle.query_selector('td:nth-child(2) small')
                    if vehicle_type and 'Police Prisoner Van' in await vehicle_type.inner_text():
                        prisoner_van = vehicle
                    else:
                        available_vehicles.append(vehicle)

                async def click_transport_button(vehicle):
                    transport_button = await vehicle.query_selector('a.btn.btn-success')
                    if transport_button:
                        await transport_button.click()
                        await page.wait_for_load_state('networkidle')

                if prisoner_van:
                    await click_transport_button(prisoner_van)
                elif available_vehicles:
                    await click_transport_button(available_vehicles[0])

                transport_buttons = await page.query_selector_all('a.btn.btn-success')
                if not transport_buttons:
                    mission_url = await page.url()
                    mission_id = mission_url.split('/')[-2]
                    release_url = f"https://www.missionchief.com/missions/{mission_id}/gefangene/entlassen"
                    await page.goto(release_url)
                    await page.wait_for_load_state('networkidle')

                transported_prisoners = 0
                if prisoner_van:
                    transported_prisoners = 5
                transported_prisoners += len(available_vehicles)

                remaining_prisoners = total_prisoners - transported_prisoners
                if remaining_prisoners > 0:
                    mission_url = await page.url()
                    await page.goto(mission_url)
                    await page.wait_for_load_state('networkidle')

    else:
        transport_requests = await page.query_selector_all('ul#radio_messages_important li')
        if transport_requests:
            vehicle_urls = []
            for request in transport_requests:
                vehicle_id = await request.get_attribute('vehicle_id')
                if vehicle_id:
                    vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
                    vehicle_urls.append(vehicle_url)

            for vehicle_url in vehicle_urls:
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
                    transport_button = await selected_hospital.query_selector('a.btn.btn-success')
                    await transport_button.click()
                    await page.wait_for_load_state('networkidle')
                else:
                    alliance_hospitals = await page.query_selector_all('table#alliance-hospitals tbody tr')
                    for alliance_hospital in alliance_hospitals:
                        transport_button = await alliance_hospital.query_selector('a.btn.btn-success')
                        if transport_button:
                            await transport_button.click()
                            await page.wait_for_load_state('networkidle')
                            break
                    else:
                        leave_button = await page.query_selector('a#leave_without_transport_no_compensation')
                        if leave_button:
                            await leave_button.click()
                            await page.wait_for_load_state('networkidle')
