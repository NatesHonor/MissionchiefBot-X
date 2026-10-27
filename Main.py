from __future__ import annotations

import asyncio
import os
import webbrowser
from pathlib import Path

from core.logging_config import configure_logging, display_exit, display_header, flush_visual_summary, get_logger
from core.runner import run_bot
from core.settings import Settings, load_settings
from core.webui import BotWebUI


PROJECT_ROOT = Path(__file__).resolve().parent
SUPPORT_URL = "https://discord.gg/AujkpRZj7D"


def _log_dir(settings: Settings | None) -> Path:
    configured = Path(settings.log_dir if settings else "logs").expanduser()
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


async def run_application(settings: Settings) -> None:
    logger = get_logger("webui")
    stop_event = asyncio.Event()
    webui = BotWebUI(host=settings.webui_host, port=settings.webui_port)
    webui.set_settings(settings)
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
    settings: Settings | None = None
    try:
        settings = load_settings()
        configure_logging(
            level=settings.log_level,
            console_enabled=settings.log_console,
            file_enabled=settings.log_file_enabled,
            visual_console=settings.log_rich_console,
            log_dir=_log_dir(settings),
        )
        display_header("Automation control runtime", {"Region": settings.region.upper(), "Workers": settings.browsers, "Mode": "Headless" if settings.headless else "Visible"})
        if settings.webui_enabled:
            asyncio.run(run_application(settings))
        else:
            asyncio.run(run_bot(settings=settings))
    except KeyboardInterrupt:
        get_logger("startup").info("Stopped by operator")
        flush_visual_summary()
        display_exit("Stopped from the keyboard (Ctrl+C).", failed=False, log_dir=_log_dir(settings))
        return 130
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        get_logger("startup").error("Configuration error: %s", error)
        flush_visual_summary()
        display_exit(f"Configuration error: {error}", log_dir=_log_dir(settings), support_url=SUPPORT_URL)
        return 2
    except Exception as error:
        get_logger("startup").exception("MissionChief Bot stopped unexpectedly")
        flush_visual_summary()
        display_exit(f"{type(error).__name__}: {error}", log_dir=_log_dir(settings), support_url=SUPPORT_URL)
        return 1
    flush_visual_summary()
    display_exit("The bot finished and exited normally.", failed=False, log_dir=_log_dir(settings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
