from utils.pretty_print import display_info, display_error

async def handle_transport_requests(context):
    page = context.pages[0]
    await page.goto("https://www.missionchief.com")
    await page.wait_for_load_state("networkidle")

    transport_requests = await page.query_selector_all("ul#radio_messages_important li")
    display_info(f"Found {len(transport_requests)} transport requests")

    vehicle_urls = []
    for request in transport_requests:
        img = await request.query_selector("img")
        if img:
            vehicle_id = await img.get_attribute("vehicle_id")
            if vehicle_id:
                vehicle_urls.append(f"https://www.missionchief.com/vehicles/{vehicle_id}")

    for vehicle_url in vehicle_urls:
        try:
            await page.goto(vehicle_url)
            await page.wait_for_load_state("networkidle")

            hospitals_table = await page.query_selector("table#own-hospitals")

            if hospitals_table:
                hospitals = await page.query_selector_all("table#own-hospitals tbody tr")
                chosen = None
                smallest_distance = float("inf")

                for hospital in hospitals:
                    name_el = await hospital.query_selector("td:first-child")
                    dist_el = await hospital.query_selector("td:nth-child(2)")
                    btn = await hospital.query_selector("a.btn.btn-success")

                    if not (name_el and dist_el and btn):
                        continue

                    try:
                        distance = float((await dist_el.inner_text()).split()[0])
                    except:
                        continue

                    if distance < smallest_distance:
                        smallest_distance = distance
                        chosen = (btn, await name_el.inner_text(), distance)

                if chosen:
                    btn, name, distance = chosen
                    await btn.click()
                    await page.wait_for_load_state("networkidle")
                    display_info(f"Transported patient to hospital '{name.strip()}' ({distance} km)")
                else:
                    display_error("No valid hospital transport option found")

            else:
                buttons = await page.query_selector_all("a.btn.btn-success")
                chosen = None
                smallest_distance = float("inf")

                for btn in buttons:
                    text = await btn.inner_text()
                    if "Distance:" not in text:
                        continue
                    try:
                        distance = float(text.split("Distance:")[1].split()[0])
                    except:
                        continue

                    if distance < smallest_distance:
                        smallest_distance = distance
                        chosen = (btn, text.strip(), distance)

                if chosen:
                    btn, label, distance = chosen
                    await btn.click()
                    await page.wait_for_load_state("networkidle")
                    display_info(f"Transported prisoners to '{label}' ({distance} km)")
                else:
                    release = await page.query_selector("a.btn.btn-xs.btn-danger")
                    if release:
                        await release.click()
                        await page.wait_for_load_state("networkidle")
                        display_info("Released prisoners (no transport available)")
                    else:
                        display_error("No prison transport or release option found")

        except Exception as e:
            display_error(f"Transport handling failed for {vehicle_url}: {e}")

    display_info("Finished handling all transport requests")
