"""Small, local-only control panel for MissionchiefBot-X.

The bot is intentionally kept independent from the launcher.  This module uses
only the Python standard library so it can run on the supported Python 3.14
installation without adding another web framework or native dependency.
"""

from __future__ import annotations

import configparser
import json
import logging
import os
import re
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .settings import DEFAULT_CONFIG_PATH, Settings, _config_path


LOGGER = logging.getLogger("missionchiefbot.webui")
LOGGER.addHandler(logging.NullHandler())
LOGGER.propagate = False
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "missionchiefbot.log"


@dataclass
class RuntimeState:
    status: str = "idle"
    message: str = "Waiting for the bot process."
    region: str = ""
    version: str = ""
    running: bool = False
    started_at: str | None = None
    updated_at: str | None = None
    settings: dict[str, Any] | None = None


# These are deliberately the non-secret settings that are useful to customize
# from the local panel.  Credentials never leave config.ini or the environment.
_SETTING_MAP: dict[str, tuple[str, str, str]] = {
    "region": ("bot", "region", "text"),
    "headless": ("browser_settings", "headless", "bool"),
    "browsers": ("browser_settings", "browsers", "int"),
    "browser_scaling": ("browser_settings", "browser_scaling", "bool"),
    "dispatch_type": ("missions", "dispatch", "text"),
    "dispatch_by_distance": ("missions", "dispatch_vehicles_by_distance", "bool"),
    "dispatch_incomplete": ("missions", "dispatch_incomplete_missions", "bool"),
    "dynamic_missions": ("missions", "dynamic_missions", "bool"),
    "include_alliance_missions": ("missions", "include_alliance_missions", "bool"),
    "max_missions": ("missions", "max_missions", "int"),
    "concurrent_missions": ("missions", "dispatch_concurrent_missions", "bool"),
    "auto_training": ("other", "auto_training", "bool"),
    "auto_recruiting": ("other", "auto_recruiting", "bool"),
    "auto_special_resources": ("other", "auto_special_resources", "bool"),
    "auto_tasks": ("other", "auto_tasks", "bool"),
    "dynamic_delays": ("delays", "dynamic_delays", "bool"),
    "dynamic_delay_missions": ("delays", "dynamic_missions", "bool"),
    "dynamic_delay_transport": ("delays", "dynamic_transport", "bool"),
    "mission_delay": ("delays", "missions", "int"),
    "other_delay": ("delays", "other", "int"),
    "dispatch_delay": ("delays", "dispatch", "int"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public_settings(settings: Settings | None) -> dict[str, Any]:
    """Return editable settings without exposing username, password, or plans."""

    if settings is None:
        return {}
    return {name: getattr(settings, name) for name in _SETTING_MAP}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _parse_update(name: str, value: Any) -> str:
    if name not in _SETTING_MAP:
        raise ValueError(f"Setting {name!r} is not editable from the WebUI.")
    kind = _SETTING_MAP[name][2]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"Setting {name!r} must be true or false.")
        return "true" if value else "false"
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Setting {name!r} must be an integer.")
        minimum = 2 if name == "browsers" else 0
        maximum = 32 if name == "browsers" else 10000
        if not minimum <= value <= maximum:
            raise ValueError(f"Setting {name!r} must be between {minimum} and {maximum}.")
        return str(value)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Setting {name!r} must be a non-empty string.")
    normalized = value.strip().lower() if name == "region" else value.strip()
    if len(normalized) > 80:
        raise ValueError(f"Setting {name!r} is too long.")
    return normalized


def save_settings(updates: dict[str, Any], path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Persist non-secret settings atomically and return the normalized values."""

    if not isinstance(updates, dict) or not updates:
        raise ValueError("Provide at least one setting to update.")

    normalized = {name: _parse_update(name, value) for name, value in updates.items()}
    config_path = _config_path(path)
    parser = configparser.ConfigParser()
    parser.read(config_path)

    for name, value in normalized.items():
        section, option, _ = _SETTING_MAP[name]
        if not parser.has_section(section):
            parser.add_section(section)
        parser.set(section, option, value)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{config_path.stem}.", suffix=".tmp", dir=config_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            parser.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, config_path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise

    typed_values: dict[str, Any] = {}
    for name, value in normalized.items():
        kind = _SETTING_MAP[name][2]
        if kind == "bool":
            typed_values[name] = value == "true"
        elif kind == "int":
            typed_values[name] = int(value)
        else:
            typed_values[name] = value
    return typed_values


def _redact_config_password(content: str) -> str:
    """Remove only the credentials password while preserving config formatting."""

    section = ""
    redacted = []
    for line in content.splitlines(keepends=True):
        section_match = re.match(r"\s*\[([^]]+)\]", line)
        if section_match:
            section = section_match.group(1).strip().casefold()
        if section == "credentials" and re.match(r"\s*password\s*=", line, re.IGNORECASE):
            newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            line = re.sub(r"(\s*password\s*=).*", rf"\1{newline}", line, flags=re.IGNORECASE)
        redacted.append(line)
    return "".join(redacted)


def read_config(path: str | os.PathLike[str] | None = None) -> str:
    """Read the local config for editing without returning the saved password."""

    config_path = _config_path(path)
    try:
        return _redact_config_password(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ""
    except OSError as error:
        raise ValueError(f"could not read config.ini: {error}") from error


def _replace_config_password(content: str, password: str) -> str:
    section = ""
    lines = []
    replaced = False
    for line in content.splitlines(keepends=True):
        section_match = re.match(r"\s*\[([^]]+)\]", line)
        if section_match:
            section = section_match.group(1).strip().casefold()
        if section == "credentials" and re.match(r"\s*password\s*=", line, re.IGNORECASE):
            newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            prefix = line[: line.index("=") + 1]
            line = f"{prefix} {password}{newline}"
            replaced = True
        lines.append(line)
    if not replaced:
        raise ValueError("config.ini must contain [credentials] password.")
    return "".join(lines)


def save_config(content: Any, path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Validate and atomically save the complete config while preserving a blank password."""

    if not isinstance(content, str) or not content.strip():
        raise ValueError("config.ini content must not be empty.")
    if len(content.encode("utf-8")) > 256 * 1024:
        raise ValueError("config.ini content is too large.")

    config_path = _config_path(path)
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(content)
    except configparser.Error as error:
        raise ValueError(f"config.ini is invalid: {error}") from error
    if not parser.has_section("credentials") or not parser.has_option("credentials", "password"):
        raise ValueError("config.ini must contain a [credentials] password setting.")

    submitted_password = parser.get("credentials", "password", raw=True).strip()
    if not submitted_password:
        existing = configparser.ConfigParser(interpolation=None)
        try:
            existing.read(config_path)
            existing_password = existing.get("credentials", "password", fallback="").strip()
        except configparser.Error as error:
            raise ValueError(f"existing config.ini is invalid: {error}") from error
        content = _replace_config_password(content, existing_password)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{config_path.stem}.", suffix=".tmp", dir=config_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, config_path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    return {"saved": True, "restart_required": True, "path": str(config_path)}


def _log_path() -> Path:
    configured = os.getenv("MISSIONCHIEF_LOG_FILE")
    return Path(configured).expanduser() if configured else DEFAULT_LOG_FILE


def read_log_tail(limit: int = 200) -> list[str]:
    """Read a bounded log tail without making the WebUI fail on log I/O errors."""

    limit = max(1, min(int(limit), 500))
    try:
        lines = _log_path().read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, ValueError):
        return []
    # WebUI request logs are not BotX runtime logs.  Filter them as well as
    # suppressing new access logging so an old log file is still readable.
    runtime_lines = [
        line for line in lines
        if "WebUI" not in line and '"/api/' not in line
    ]
    return runtime_lines[-limit:]


class BotWebUI:
    """Threaded localhost server exposing runtime status and safe bot controls."""

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        config_path: str | os.PathLike[str] | None = None,
    ) -> None:
        self.host = host or os.getenv("MISSIONCHIEF_WEBUI_HOST", DEFAULT_HOST)
        self.port = int(port if port is not None else os.getenv("MISSIONCHIEF_WEBUI_PORT", DEFAULT_PORT))
        if not 0 <= self.port <= 65535:
            raise ValueError("MISSIONCHIEF_WEBUI_PORT must be between 0 and 65535.")
        self.config_path = config_path or os.getenv("MISSIONCHIEF_CONFIG_FILE") or DEFAULT_CONFIG_PATH
        self._state = RuntimeState()
        self._lock = threading.RLock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._start_callback: Callable[[], None] | None = None
        self._stop_callback: Callable[[], None] | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def url(self) -> str:
        address = self._server.server_address if self._server else (self.host, self.port)
        return f"http://{address[0]}:{address[1]}"

    def set_control_callbacks(
        self,
        *,
        start: Callable[[], None] | None = None,
        stop: Callable[[], None] | None = None,
    ) -> None:
        if start is not None:
            self._start_callback = start
        if stop is not None:
            self._stop_callback = stop

    def set_settings(self, settings: Settings | None) -> None:
        with self._lock:
            self._state.settings = public_settings(settings)
            if settings is not None:
                self._state.region = settings.region

    def update(
        self,
        *,
        status: str | None = None,
        message: str | None = None,
        settings: Settings | None = None,
        running: bool | None = None,
        region: str | None = None,
        version: str | None = None,
    ) -> None:
        with self._lock:
            if status is not None:
                self._state.status = status
            if message is not None:
                self._state.message = message
            if running is not None:
                self._state.running = running
            if region is not None:
                self._state.region = region
            if version is not None:
                self._state.version = version
            if settings is not None:
                self._state.settings = public_settings(settings)
            if running:
                self._state.started_at = self._state.started_at or _now()
            self._state.updated_at = _now()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = _json_safe(asdict(self._state))
        state["webui"] = {"url": self.url, "local_only": self.host in {"127.0.0.1", "localhost", "::1"}}
        state["recent_logs"] = read_log_tail()
        return state

    def start(self) -> bool:
        if self._server is not None:
            return True

        handler = self._make_handler()
        try:
            server = ThreadingHTTPServer((self.host, self.port), handler)
        except OSError as error:
            LOGGER.warning("WebUI could not start on %s:%s: %s", self.host, self.port, error)
            return False
        server.daemon_threads = True
        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever,
            name="missionchief-webui",
            daemon=True,
        )
        self._thread.start()
        LOGGER.info("Local WebUI available at %s", self.url)
        print(f"Local WebUI available at {self.url}")
        return True

    def stop(self) -> None:
        server, thread = self._server, self._thread
        self._server = None
        self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _make_handler(self):
        webui = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "MissionchiefBotX-WebUI/1.0"

            def log_message(self, format: str, *args: Any) -> None:
                # Polling the page must never pollute the BotX runtime log.
                return

            def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
                encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(encoded)

            def _send_html(self) -> None:
                encoded = DASHBOARD_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(encoded)

            def _body(self) -> dict[str, Any]:
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length > 128 * 1024:
                        raise ValueError("request body is too large")
                    value = json.loads(self.rfile.read(length) or b"{}")
                except (ValueError, json.JSONDecodeError) as error:
                    raise ValueError(f"invalid JSON request: {error}") from error
                if not isinstance(value, dict):
                    raise ValueError("request body must be a JSON object")
                return value

            def do_GET(self) -> None:  # noqa: N802 - stdlib HTTP handler API
                path = urlsplit(self.path).path
                if path == "/":
                    self._send_html()
                elif path == "/api/health":
                    self._send_json({"ok": True, "service": "missionchiefbotx-webui"})
                elif path == "/api/status":
                    self._send_json(webui.snapshot())
                elif path == "/api/logs":
                    self._send_json({"lines": read_log_tail()})
                elif path == "/api/settings":
                    with webui._lock:
                        settings = dict(webui._state.settings or {})
                    self._send_json({"settings": settings, "restart_required": True})
                elif path == "/api/config":
                    self._send_json(
                        {
                            "content": read_config(webui.config_path),
                            "restart_required": True,
                        }
                    )
                else:
                    self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:  # noqa: N802 - stdlib HTTP handler API
                path = urlsplit(self.path).path
                try:
                    body = self._body()
                    if path == "/api/settings":
                        saved = save_settings(body, webui.config_path)
                        with webui._lock:
                            if webui._state.settings is None:
                                webui._state.settings = {}
                            webui._state.settings.update(saved)
                        self._send_json(
                            {
                                "saved": True,
                                "settings": saved,
                                "restart_required": True,
                                "message": "Settings saved. Restart the bot to apply them.",
                            }
                        )
                    elif path == "/api/config":
                        result = save_config(body.get("content"), webui.config_path)
                        self._send_json(
                            {
                                **result,
                                "message": "config.ini saved. Restart the bot to apply the changes.",
                            }
                        )
                    elif path == "/api/control":
                        self._control(body)
                    else:
                        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                except ValueError as error:
                    self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                except OSError as error:
                    LOGGER.exception("WebUI request failed")
                    self._send_json({"error": f"could not save settings: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

            def _control(self, body: dict[str, Any]) -> None:
                action = body.get("action")
                callback = webui._start_callback if action == "start" else webui._stop_callback if action == "stop" else None
                if action not in {"start", "stop"}:
                    self._send_json({"error": "action must be start or stop"}, HTTPStatus.BAD_REQUEST)
                    return
                if callback is None:
                    self._send_json(
                        {"error": f"{action} control cannot be used in this process"},
                        HTTPStatus.CONFLICT,
                    )
                    return
                callback()
                self._send_json({"accepted": True, "action": action})

        return Handler


DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MissionchiefBot-X</title>
<style>
:root { color-scheme:dark; --background:#071a2d; --surface:#0d2741; --border:#24557b; --text:#f3f8fc; --muted:#9db9cf; --blue:#238ddd; --red:#d75b6d; }
* { box-sizing:border-box; } body { margin:0; background:var(--background); color:var(--text); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
.layout { display:grid; grid-template-columns:170px minmax(0,1fr); min-height:100vh; } .sidebar { padding:22px 12px; border-right:1px solid var(--border); } .sidebar h1 { padding:0 10px 20px; font-size:18px; } .tabs { display:grid; gap:4px; } .tab { width:100%; padding:10px; border:1px solid transparent; border-radius:4px; color:var(--muted); background:transparent; text-align:left; cursor:pointer; font:inherit; } .tab:hover { color:var(--text); background:#123453; } .tab.active { color:var(--text); border-color:var(--blue); background:#123b5c; }
.page { width:min(100% - 40px,960px); margin:0 auto; padding:30px 0 44px; } header { border-bottom:1px solid var(--border); padding-bottom:18px; margin-bottom:18px; } h1,h2,p { margin:0; } h1 { font-size:24px; } h2 { font-size:17px; } header p,.message,.label,.note,footer { color:var(--muted); } header p { margin-top:4px; }
.view { display:none; } .view.active { display:block; } .summary { display:flex; flex-wrap:wrap; gap:28px; padding:16px 0 20px; } .summary div { min-width:120px; } .label { display:block; font-size:12px; } .value { display:block; margin-top:2px; font-weight:650; } .message { margin-bottom:18px; }
.section { margin-top:18px; padding:18px; border:1px solid var(--border); background:var(--surface); } .section-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px; } .actions { display:flex; gap:8px; flex-wrap:wrap; }
button { border:1px solid var(--border); border-radius:4px; padding:9px 14px; color:var(--text); background:#123453; cursor:pointer; font:inherit; } button:hover { border-color:#52a8e7; } button.start { background:var(--blue); border-color:var(--blue); } button.stop { background:#642b38; border-color:var(--red); }
.logs { height:calc(100vh - 210px); min-height:280px; overflow:auto; margin:0; padding:12px; white-space:pre-wrap; overflow-wrap:anywhere; background:#04111e; border:1px solid #163b5c; color:#d5e9f8; font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; } .option { display:flex; align-items:center; gap:7px; color:var(--muted); font-size:12px; }
.config { width:100%; min-height:560px; padding:12px; resize:vertical; color:var(--text); background:#071a2d; border:1px solid var(--border); border-radius:4px; font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; } .config:focus { outline:2px solid #238ddd66; border-color:#52a8e7; } .note { min-height:20px; padding-top:10px; } footer { margin-top:20px; font-size:12px; }
@media (max-width:650px) { .layout { grid-template-columns:1fr; } .sidebar { padding:12px; border-right:0; border-bottom:1px solid var(--border); } .sidebar h1 { padding:0 0 10px; } .tabs { grid-template-columns:repeat(3,1fr); } .tab { text-align:center; } .page { width:min(100% - 20px,960px); padding-top:18px; } .logs { height:60vh; } }
</style>
</head>
<body>
<div class="layout"><aside class="sidebar"><h1>MissionchiefBot-X</h1><nav class="tabs"><button class="tab active" data-view="dashboard">Overview</button><button class="tab" data-view="logs">Console</button><button class="tab" data-view="settings">Configuration</button></nav></aside>
<main class="page"><header><h1 id="page-title">Overview</h1><p>Local BotX control page</p></header>
<section id="view-dashboard" class="view active"><section class="summary"><div><span class="label">Status</span><span id="status" class="value">Ready</span></div><div><span class="label">Region</span><span id="region" class="value">—</span></div><div><span class="label">Version</span><span id="version" class="value">—</span></div></section><p id="message" class="message">Waiting for the bot.</p><section class="section"><div class="section-head"><h2>Bot control</h2><div class="actions"><button class="start" onclick="control('start')">Start bot</button><button class="stop" onclick="control('stop')">Stop bot</button></div></div><div id="control-note" class="note"></div></section></section>
<section id="view-logs" class="view"><section class="section" style="margin-top:0"><div class="section-head"><h2>MissionChief output</h2><div class="actions"><label class="option"><input id="auto-scroll" type="checkbox"> Auto-scroll</label><button onclick="refresh()">Refresh</button></div></div><pre id="logs" class="logs">No MissionChief output yet.</pre></section></section>
<section id="view-settings" class="view"><section class="section" style="margin-top:0"><div class="section-head"><h2>Complete config.ini</h2><span class="label">Saved for next start</span></div><p class="message">Edit the complete BotX configuration here. The password is hidden when loaded; leaving it blank keeps the saved password.</p><textarea id="config" class="config" spellcheck="false" aria-label="Complete BotX configuration"></textarea><div class="actions" style="margin-top:16px"><button class="start" onclick="saveConfig()">Save config.ini</button></div><div id="settings-note" class="note"></div></section></section>
<footer>Bot settings are read again when the bot starts.</footer></main></div>
<script>
const $ = (id) => document.getElementById(id);
let autoScroll = localStorage.getItem('missionchief.autoScroll') !== 'false';
let configDirty = false;
function showView(view) { document.querySelectorAll('.view').forEach((item)=>item.classList.toggle('active',item.id==='view-'+view)); document.querySelectorAll('.tab').forEach((item)=>item.classList.toggle('active',item.dataset.view===view)); $('page-title').textContent = view === 'dashboard' ? 'Overview' : view === 'logs' ? 'Console' : 'Configuration'; if(view === 'settings' && !$('config').value) loadConfig(); }
document.querySelectorAll('.tab').forEach((tab)=>tab.addEventListener('click',()=>showView(tab.dataset.view)));
$('auto-scroll').checked=autoScroll; $('auto-scroll').addEventListener('change',()=>{ autoScroll=$('auto-scroll').checked; localStorage.setItem('missionchief.autoScroll',String(autoScroll)); if(autoScroll) $('logs').scrollTop=$('logs').scrollHeight; });
function updateLogs(lines) { const logs=$('logs'); const wasAtBottom=logs.scrollHeight-logs.scrollTop-logs.clientHeight<24; logs.textContent=(lines || []).join('\n') || 'No MissionChief output yet.'; if(autoScroll || wasAtBottom) logs.scrollTop=logs.scrollHeight; }
async function refresh() { try { const response=await fetch('/api/status',{cache:'no-store'}); const data=await response.json(); $('status').textContent=data.status || '—'; $('region').textContent=(data.region || '—').toUpperCase(); $('version').textContent=data.version || '—'; $('message').textContent=data.message || ''; updateLogs(data.recent_logs); } catch(error) { $('message').textContent='Could not load bot status.'; } }
async function loadConfig() { try { const response=await fetch('/api/config',{cache:'no-store'}); const data=await response.json(); if(!configDirty) $('config').value=data.content || ''; } catch(error) { $('settings-note').textContent='config.ini could not be loaded.'; } }
async function saveConfig() { $('settings-note').textContent='Saving…'; try { const response=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:$('config').value})}); const data=await response.json(); $('settings-note').textContent=data.message || data.error || 'Saved.'; if(response.ok) configDirty=false; } catch(error) { $('settings-note').textContent='config.ini could not be saved.'; } }
async function control(action) { $('control-note').textContent='Sending '+action+' request…'; try { const response=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})}); const data=await response.json(); $('control-note').textContent=data.accepted ? action+' request accepted.' : (data.error || 'Request failed.'); setTimeout(refresh,300); } catch(error) { $('control-note').textContent='Control request failed.'; } }
$('config').addEventListener('input',()=>{ configDirty=true; });
refresh(); setInterval(refresh,2000);
</script>
</body></html>"""
