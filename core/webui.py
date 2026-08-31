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
    return lines[-limit:]


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
                LOGGER.info("WebUI %s - %s", self.address_string(), format % args)

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
                        {"error": f"{action} control is unavailable in this process"},
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
<title>MissionchiefBot-X Control</title>
<style>
:root { color-scheme: dark; --bg:#071a2d; --panel:#0c2742; --panel2:#102f4d; --line:#1d527d; --text:#edf7ff; --muted:#8fb5d4; --blue:#28a8ff; --cyan:#4de4ff; --green:#43df9a; --red:#ff7083; }
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--text); background:radial-gradient(circle at 85% -10%,#12456d 0,transparent 36%),var(--bg); }
.shell { width:min(1180px,calc(100% - 36px)); margin:0 auto; padding:28px 0 52px; }
header { display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:26px; }
.brand { display:flex; align-items:center; gap:13px; }
.mark { width:42px; height:42px; display:grid; place-items:center; color:var(--bg); font-weight:900; border-radius:12px; background:linear-gradient(135deg,var(--cyan),var(--blue)); box-shadow:0 8px 24px #0a8ee455; }
h1,h2,h3,p { margin:0; } h1 { font-size:22px; letter-spacing:.01em; } h2 { font-size:17px; } h3 { font-size:13px; text-transform:uppercase; letter-spacing:.12em; color:var(--cyan); }
.sub,.muted { color:var(--muted); } .sub { margin-top:2px; }
.badge { display:inline-flex; align-items:center; gap:8px; padding:7px 12px; border:1px solid var(--line); border-radius:999px; color:var(--muted); }
.dot { width:8px; height:8px; border-radius:50%; background:var(--muted); } .dot.live { background:var(--green); box-shadow:0 0 12px var(--green); } .dot.error { background:var(--red); }
.hero { display:flex; justify-content:space-between; gap:24px; padding:26px; border:1px solid var(--line); border-radius:18px; background:linear-gradient(135deg,#0e3151dd,#0a2036dd); box-shadow:0 20px 48px #0003; }
.hero p { color:var(--muted); max-width:650px; margin-top:8px; }
.hero-meta { display:grid; grid-template-columns:repeat(3,minmax(90px,1fr)); gap:18px; min-width:300px; text-align:right; } .metric { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.1em; } .metric strong { display:block; margin-top:3px; color:var(--text); font-size:16px; text-transform:none; letter-spacing:0; }
.grid { display:grid; grid-template-columns:minmax(0,1.45fr) minmax(300px,.85fr); gap:18px; margin-top:18px; }
.card { min-width:0; padding:21px; border:1px solid var(--line); border-radius:16px; background:#0b243bdd; } .card-head { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:16px; }
.controls { display:flex; gap:10px; flex-wrap:wrap; } button { border:1px solid var(--line); border-radius:9px; padding:10px 15px; color:var(--text); background:var(--panel2); cursor:pointer; font-weight:650; } button:hover { border-color:var(--cyan); background:#164267; } button.primary { border-color:transparent; background:linear-gradient(135deg,#168ff1,#20b8e8); } button.danger { color:#ffdce1; border-color:#934052; }
.logs { height:390px; overflow:auto; padding:16px; white-space:pre-wrap; overflow-wrap:anywhere; border:1px solid #143b5d; border-radius:11px; background:#061525; color:#c6e9ff; font:12px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:13px; } label { display:flex; flex-direction:column; gap:6px; color:var(--muted); font-size:12px; } input,select { width:100%; padding:10px 11px; color:var(--text); border:1px solid var(--line); border-radius:8px; outline:none; background:#071a2d; } input:focus,select:focus { border-color:var(--cyan); box-shadow:0 0 0 3px #4de4ff22; } .check { flex-direction:row; align-items:center; padding-top:24px; } .check input { width:auto; accent-color:var(--blue); }
.notice { min-height:22px; margin-top:13px; color:var(--cyan); } footer { margin-top:18px; color:var(--muted); text-align:center; font-size:12px; }
@media (max-width:820px) { .hero { flex-direction:column; } .hero-meta { min-width:0; text-align:left; } .grid { grid-template-columns:1fr; } } @media (max-width:520px) { .shell { width:min(100% - 22px,1180px); padding-top:16px; } header { align-items:flex-start; flex-direction:column; } .form-grid { grid-template-columns:1fr; } .check { padding-top:0; } }
</style>
</head>
<body>
<main class="shell">
<header><div class="brand"><div class="mark">MC</div><div><h1>MissionchiefBot-X</h1><p class="sub">Local bot control panel</p></div></div><div id="connection" class="badge"><span class="dot"></span>Connecting</div></header>
<section class="hero"><div><h3>Runtime overview</h3><h2 id="message" style="margin-top:9px">Loading bot state…</h2><p>Monitor mission dispatch, background work, and the bot log without opening the launcher. This panel is bound to the local machine.</p></div><div class="hero-meta"><div><span class="metric">Status</span><strong id="status">—</strong></div><div><span class="metric">Region</span><strong id="region">—</strong></div><div><span class="metric">Version</span><strong id="version">—</strong></div></div></section>
<section class="grid">
<div class="card"><div class="card-head"><div><h3>Console output</h3><h2 style="margin-top:5px">Live activity</h2></div><button onclick="refresh()">Refresh</button></div><pre id="logs" class="logs">Waiting for log output…</pre></div>
<div class="card"><div class="card-head"><div><h3>Bot control</h3><h2 style="margin-top:5px">Process actions</h2></div></div><p class="muted" style="margin-bottom:16px">Start or stop the BotX runtime. A stop request lets the bot close its browser contexts cleanly.</p><div class="controls"><button class="primary" onclick="control('start')">Start bot</button><button class="danger" onclick="control('stop')">Stop bot</button></div><div id="control-note" class="notice"></div></div>
<div class="card" style="grid-column:1/-1"><div class="card-head"><div><h3>Settings customization</h3><h2 style="margin-top:5px">Local runtime settings</h2></div><span class="muted">Saved to config.ini</span></div><form id="settings-form"><div class="form-grid"><label>Region<select name="region"><option value="us">United States</option><option value="uk">United Kingdom</option><option value="ger">Germany</option><option value="swe">Sweden</option><option value="pl">Poland</option><option value="fr">France</option><option value="nld">Netherlands</option><option value="pt">Portugal</option><option value="aus">Australia</option><option value="dk">Denmark</option></select></label><label>Dispatch type<input name="dispatch_type" type="text" maxlength="80"></label><label>Browsers<input name="browsers" type="number" min="2" max="32"></label><label>Mission delay (seconds)<input name="mission_delay" type="number" min="0" max="10000"></label><label>Transport delay (seconds)<input name="other_delay" type="number" min="0" max="10000"></label><label>Dispatch delay (seconds)<input name="dispatch_delay" type="number" min="0" max="10000"></label><label class="check"><input name="headless" type="checkbox"> Run browsers headless</label><label class="check"><input name="concurrent_missions" type="checkbox"> Dispatch missions concurrently</label></div><div class="controls" style="margin-top:17px"><button class="primary" type="submit">Save settings</button></div><div id="settings-note" class="notice"></div></form></div>
</section><footer>MissionchiefBot-X • local-only WebUI • Changes apply after restart</footer>
</main>
<script>
const $ = (id) => document.getElementById(id);
function setConnection(online) { $('connection').innerHTML = `<span class="dot ${online ? 'live' : 'error'}"></span>${online ? 'Connected' : 'Unavailable'}`; }
function fillSettings(settings) { const form=$('settings-form'); Object.entries(settings || {}).forEach(([key,value]) => { const input=form.elements[key]; if (!input) return; if (input.type === 'checkbox') input.checked=Boolean(value); else input.value=value; }); }
async function refresh() { try { const response=await fetch('/api/status',{cache:'no-store'}); if(!response.ok) throw new Error('status '+response.status); const data=await response.json(); setConnection(true); $('status').textContent=data.status || '—'; $('region').textContent=(data.region || '—').toUpperCase(); $('version').textContent=data.version || '—'; $('message').textContent=data.message || ''; $('logs').textContent=(data.recent_logs || []).join('\n') || 'No log output yet.'; fillSettings(data.settings); } catch(error) { setConnection(false); $('message').textContent='WebUI cannot reach the bot process.'; } }
async function control(action) { $('control-note').textContent='Sending '+action+' request…'; try { const response=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})}); const data=await response.json(); $('control-note').textContent=data.accepted ? action+' request accepted.' : (data.error || 'Request failed.'); if(data.accepted) setTimeout(refresh,300); } catch(error) { $('control-note').textContent='Control request failed.'; } }
$('settings-form').addEventListener('submit',async(event)=>{ event.preventDefault(); const form=new FormData(event.target); const body={region:form.get('region'),dispatch_type:form.get('dispatch_type'),browsers:Number(form.get('browsers')),mission_delay:Number(form.get('mission_delay')),other_delay:Number(form.get('other_delay')),dispatch_delay:Number(form.get('dispatch_delay')),headless:form.get('headless')==='on',concurrent_missions:form.get('concurrent_missions')==='on'}; $('settings-note').textContent='Saving…'; try { const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); const data=await response.json(); $('settings-note').textContent=data.message || data.error || 'Saved.'; } catch(error) { $('settings-note').textContent='Settings could not be saved.'; } });
refresh(); setInterval(refresh,2000);
</script>
</body></html>"""
