from __future__ import annotations

import asyncio
import os
import webbrowser
from pathlib import Path

from core.logging_config import configure_logging, display_header, flush_visual_summary, get_logger
from core.runner import run_bot
from core.settings import Settings, load_settings
from core.webui import BotWebUI


PROJECT_ROOT = Path(__file__).resolve().parent
SUPPORT_URL = "https://discord.gg/AujkpRZj7D"


def display_failure_help(log_file: str) -> None:
    """Tell users where to find diagnostics and community support."""
    log_path = Path(log_file)
    if not log_path.is_absolute():
        log_path = PROJECT_ROOT / log_path
    print(f"Check the logs for more information: {log_path}")
    print("       __      __")
    print("    .-'  `----'  `-.")
    print("   /   .--.  .--.   \\")
    print("  |   (    \\/    )   |  DISCORD SUPPORT")
    print("   \\   `--'  `--'   /")
    print("    `-._  /\\  _.-'")
    print(f"Need help? Join us at {SUPPORT_URL}")


async def run_application(settings: Settings) -> None:
    logger = get_logger("webui")
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    webui = BotWebUI(host=settings.webui_host, port=settings.webui_port)
    webui.set_settings(settings)
    # BotWebUI's public callback API currently only accepts a positional stop
    # callback. Keep the asyncio event update thread-safe because requests are
    # handled by the WebUI's HTTP server thread.
    webui.set_control_callbacks(
        lambda: loop.call_soon_threadsafe(stop_event.set),
    )
    try:
        webui.start()
        logger.info("Local control panel available at %s", webui.url)
        try:
            webbrowser.open(webui.url)
        except (OSError, webbrowser.Error):
            logger.warning("Could not open the control panel automatically. Open %s manually.", webui.url)
        while not stop_event.is_set():
            webui.update(status="starting", message="Starting automation runtime.", running=True)
            bot_task = asyncio.create_task(run_bot(settings=settings, webui=webui))
            stop_task = asyncio.create_task(stop_event.wait())
            done, _ = await asyncio.wait({bot_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
            if stop_task in done:
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    pass
                break
            stop_task.cancel()
            try:
                await stop_task
            except asyncio.CancelledError:
                pass
            error = bot_task.exception()
            if error is not None:
                webui.update_state(status="error", message=str(error), running=False)
                logger.exception("Automation runtime stopped unexpectedly", exc_info=error)
                raise error
            webui.update_state(status="idle", message="Bot stopped. Waiting for a start request.", running=False)
            await asyncio.to_thread(stop_event.wait)
            stop_event.clear()
    finally:
        webui.update_state(status="stopped", message="Application stopped.", running=False)
        webui.stop()


def main() -> int:
    os.chdir(PROJECT_ROOT)
    try:
        settings = load_settings()
        configure_logging()
        display_header("Automation control runtime", {"Region": settings.region.upper(), "Workers": settings.browsers, "Mode": "Headless" if settings.headless else "Visible"})
        if settings.webui_enabled:
            asyncio.run(run_application(settings))
        else:
            asyncio.run(run_bot(settings=settings))
    except KeyboardInterrupt:
        get_logger("startup").info("Stopped by operator")
        return 130
    except (FileNotFoundError, ValueError) as error:
        get_logger("startup").error("Configuration error: %s", error)
        return 2
    except Exception:
        get_logger("startup").exception("MissionChief Bot stopped unexpectedly")
        return 1
    finally:
        flush_visual_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
