import asyncio
import os
import sys
from pathlib import Path

from core.runner import run_bot
from core.webui import BotWebUI


PROJECT_ROOT = Path(__file__).resolve().parent


async def run_application() -> None:
    """Keep the local control panel alive while the bot can be restarted."""

    webui = BotWebUI()
    webui.start()
    loop = asyncio.get_running_loop()
    current_task: asyncio.Task | None = None
    current_stop_event: asyncio.Event | None = None

    def report_finished(task: asyncio.Task) -> None:
        if task is not current_task or task.cancelled():
            return
        try:
            task.result()
        except Exception as error:
            print(f"MissionChief Bot could not start: {error}", file=sys.stderr)
            webui.update(
                status="error",
                message=f"Bot could not start: {error}",
                running=False,
            )

    def start_bot() -> None:
        nonlocal current_task, current_stop_event
        if current_task is not None and not current_task.done():
            return
        current_stop_event = asyncio.Event()
        current_task = asyncio.create_task(
            run_bot(webui=webui, stop_event=current_stop_event),
            name="missionchief-bot-runtime",
        )
        current_task.add_done_callback(report_finished)

    def request_start() -> None:
        loop.call_soon_threadsafe(start_bot)

    def request_stop() -> None:
        if current_stop_event is not None:
            loop.call_soon_threadsafe(current_stop_event.set)

    webui.set_control_callbacks(start=request_start, stop=request_stop)
    start_bot()
    try:
        await asyncio.Event().wait()
    finally:
        request_stop()
        if current_task is not None:
            await asyncio.gather(current_task, return_exceptions=True)
        webui.stop()


def main() -> int:
    """Run the bot from any working directory with a useful exit status."""

    os.chdir(PROJECT_ROOT)
    try:
        asyncio.run(run_application())
    except KeyboardInterrupt:
        print("MissionChief Bot stopped.")
    except Exception as error:
        print(f"MissionChief Bot could not start: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
