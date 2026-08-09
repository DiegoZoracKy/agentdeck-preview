"""Browser conformance probe for portable Instrument Game Stages."""

from __future__ import annotations

import json
import mimetypes
import threading
from hashlib import sha256
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Sequence, TypedDict
from urllib.parse import unquote, urlsplit

from agentdeck.core.artifact_safety import ensure_contained_path, require_json_value

STAGE_PROTOCOL = "agentdeck-stage/1.0"


class _StageViewport(TypedDict):
    id: str
    width: int
    height: int


STAGE_VIEWPORTS: tuple[_StageViewport, ...] = (
    {"id": "desktop", "width": 1280, "height": 720},
    {"id": "mobile", "width": 390, "height": 844},
)


class StageCertificationError(RuntimeError):
    """Base failure for custom Stage certification."""


class StageIsolationError(StageCertificationError):
    """Raised when a Stage escapes its declared offline browser boundary."""


class StageRuntimeError(StageCertificationError):
    """Raised when a Stage cannot satisfy the host protocol or visual probe."""


def _harness_html(*, surface: Mapping[str, Any], entry_url: str) -> bytes:
    encoded = json.dumps(surface, sort_keys=True, ensure_ascii=True, allow_nan=False).replace(
        "</", "<\\/"
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>html,body,#stage{{width:100%;height:100%;margin:0;overflow:hidden}}#stage{{border:0}}</style>
</head><body><script>
(() => {{
  const protocol = {json.dumps(STAGE_PROTOCOL)};
  const surface = {encoded};
  let stageFrame = null;
  window.__agentdeckProbe = {{state:"booting",last_rendered:null,messages:[],errors:[]}};
  const send = payload => stageFrame.contentWindow.postMessage(payload, "*");
  const exactKeys = (value, keys) =>
    Object.keys(value).sort().join(",") === [...keys].sort().join(",");
  window.addEventListener("message", event => {{
    if (!stageFrame || event.source !== stageFrame.contentWindow) return;
    const data = event.data;
    if (!data || typeof data !== "object") {{
      window.__agentdeckProbe.errors.push("non-object stage message");
      return;
    }}
    window.__agentdeckProbe.messages.push(data);
    if (data.protocol !== protocol) {{
      window.__agentdeckProbe.errors.push("protocol mismatch");
      return;
    }}
    if (data.type === "agentdeck:stage-ready") {{
      if (!exactKeys(data, ["type", "protocol"])) {{
        window.__agentdeckProbe.errors.push("invalid ready acknowledgement");
        return;
      }}
      window.__agentdeckProbe.state = "ready";
      send({{type:"agentdeck:stage-load",protocol,match_surface:surface}});
    }} else if (data.type === "agentdeck:stage-loaded") {{
      if (!exactKeys(data, ["type", "protocol", "match_id", "frame_count"])) {{
        window.__agentdeckProbe.errors.push("invalid loaded acknowledgement");
        return;
      }}
      window.__agentdeckProbe.loaded = data;
      window.__agentdeckProbe.state = "loaded";
    }} else if (data.type === "agentdeck:stage-rendered") {{
      if (!exactKeys(data, ["type", "protocol", "frame_index"])) {{
        window.__agentdeckProbe.errors.push("invalid rendered acknowledgement");
        return;
      }}
      window.__agentdeckProbe.last_rendered = data.frame_index;
    }} else if (data.type === "agentdeck:stage-error") {{
      if (!exactKeys(data, ["type", "protocol", "message"])) {{
        window.__agentdeckProbe.errors.push("invalid error acknowledgement");
        return;
      }}
      window.__agentdeckProbe.errors.push(String(data.message || "stage error"));
    }} else {{
      window.__agentdeckProbe.errors.push("unknown stage message");
    }}
  }});
  window.__agentdeckRender = frameIndex => {{
    const frame = surface.frames[frameIndex];
    window.__agentdeckProbe.last_rendered = null;
    send({{type:"agentdeck:stage-render",protocol,frame_index:frameIndex,frame}});
  }};
  stageFrame = document.createElement("iframe");
  stageFrame.id = "stage";
  stageFrame.setAttribute("sandbox", "allow-scripts");
  stageFrame.src = {json.dumps(entry_url)};
  document.body.appendChild(stageFrame);
}})();
</script></body></html>""".encode("utf-8")


def _handler_type(*, presentation_root: Path, harness: bytes) -> type[BaseHTTPRequestHandler]:
    class StageRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            del format, args

        def _headers(self, *, content_type: str, harness_response: bool) -> None:
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            if harness_response:
                policy = (
                    "default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'unsafe-inline'; "
                    "frame-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'"
                )
            else:
                policy = (
                    "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
                    "font-src 'self' data:; media-src 'self' data: blob:; connect-src 'none'; "
                    "object-src 'none'; frame-src 'none'; worker-src 'self' blob:; "
                    "base-uri 'none'; form-action 'none'"
                )
            self.send_header("Content-Security-Policy", policy)
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            request_path = unquote(urlsplit(self.path).path)
            if request_path == "/__agentdeck__/harness.html":
                self.send_response(200)
                self._headers(content_type="text/html; charset=utf-8", harness_response=True)
                self.wfile.write(harness)
                return
            if not request_path.startswith("/stage/"):
                self.send_error(404)
                return
            relative = request_path.removeprefix("/stage/")
            try:
                target = ensure_contained_path(presentation_root, presentation_root / relative)
            except ValueError:
                self.send_error(403)
                return
            if not target.is_file():
                self.send_error(404)
                return
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_response(200)
            self._headers(content_type=content_type, harness_response=False)
            self.wfile.write(target.read_bytes())

    return StageRequestHandler


@contextmanager
def _serve_stage(*, presentation_root: Path, harness: bytes) -> Iterator[str]:
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        _handler_type(presentation_root=presentation_root, harness=harness),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host = str(server.server_address[0])
        port = int(server.server_address[1])
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _visual_fingerprint(payload: bytes, *, field: str) -> str:
    try:
        from PIL import Image, ImageStat
    except ImportError as exc:  # pragma: no cover - exercised by dependency preflight
        raise StageRuntimeError(
            "Game Stage certification requires the optional 'stage' dependencies"
        ) from exc
    image = Image.open(BytesIO(payload)).convert("RGB").resize((64, 64))
    variance = sum(ImageStat.Stat(image).var)
    colors = image.getcolors(maxcolors=64 * 64) or []
    if variance < 1.0 or len(colors) < 2:
        raise StageRuntimeError(f"{field} produced blank visual output")
    return sha256(image.tobytes()).hexdigest()


def certify_game_stage(
    *,
    package_root: Path,
    viewer: str,
    surfaces: Sequence[Mapping[str, Any]],
    output_root: Path | None,
) -> Dict[str, Any]:
    """Run the technology-neutral Stage protocol against one certified Match Surface."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised by dependency preflight
        raise StageRuntimeError(
            "Game Stage certification requires `pip install agentdeck-ai[stage]`"
        ) from exc

    if not surfaces:
        raise StageRuntimeError("Game Stage certification requires a Match Surface")
    surface = dict(surfaces[0])
    require_json_value(surface, field="Game Stage Match Surface")
    frames = surface.get("frames")
    if not isinstance(frames, list) or not frames:
        raise StageRuntimeError("Game Stage Match Surface has no gameplay frames")
    match_id = str((surface.get("match") or {}).get("match_id", ""))

    presentation_root = ensure_contained_path(package_root, package_root / "presentation")
    entry = ensure_contained_path(package_root, package_root / viewer)
    try:
        entry_relative = entry.relative_to(presentation_root).as_posix()
    except ValueError as exc:
        raise StageIsolationError("Game Stage entry leaves presentation/") from exc

    harness = _harness_html(surface=surface, entry_url=f"/stage/{entry_relative}")
    results = []
    artifact_names: list[str] = []
    with _serve_stage(presentation_root=presentation_root, harness=harness) as origin:
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as exc:
            raise StageRuntimeError(
                "Chromium is unavailable; run `python -m playwright install chromium`"
            ) from exc
        try:
            for viewport in STAGE_VIEWPORTS:
                context = browser.new_context(
                    viewport={"width": viewport["width"], "height": viewport["height"]},
                    reduced_motion="reduce",
                )
                blocked: list[str] = []
                console_errors: list[str] = []
                page_errors: list[str] = []

                def route_request(route: Any) -> None:
                    parsed = urlsplit(route.request.url)
                    allowed = parsed.scheme in {"data", "blob"} or (
                        f"{parsed.scheme}://{parsed.netloc}" == origin
                        and (
                            parsed.path == "/__agentdeck__/harness.html"
                            or parsed.path.startswith("/stage/")
                        )
                    )
                    if allowed:
                        route.continue_()
                    else:
                        blocked.append(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
                        route.abort()

                context.route("**/*", route_request)
                page = context.new_page()
                page.on(
                    "console",
                    lambda message: (
                        console_errors.append(message.text) if message.type == "error" else None
                    ),
                )
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                try:
                    page.goto(
                        f"{origin}/__agentdeck__/harness.html",
                        wait_until="domcontentloaded",
                    )
                    page.wait_for_function(
                        "window.__agentdeckProbe && window.__agentdeckProbe.state === 'loaded'",
                        timeout=10_000,
                    )
                    loaded = page.evaluate("window.__agentdeckProbe.loaded")
                    if not isinstance(loaded, dict) or (
                        loaded.get("match_id") != match_id
                        or loaded.get("frame_count") != len(frames)
                    ):
                        raise StageRuntimeError("Game Stage loaded acknowledgement is not exact")

                    probe_frames = [0, len(frames) - 1]
                    frame_results = []
                    fingerprints = []
                    for label, frame_index in zip(("first", "last"), probe_frames):
                        page.evaluate(
                            "frameIndex => window.__agentdeckRender(frameIndex)", frame_index
                        )
                        page.wait_for_function(
                            "frameIndex => window.__agentdeckProbe.last_rendered === frameIndex",
                            arg=frame_index,
                            timeout=10_000,
                        )
                        page.wait_for_timeout(100)
                        page.evaluate(
                            "() => new Promise(resolve => requestAnimationFrame(() => "
                            "requestAnimationFrame(resolve)))"
                        )
                        screenshot = page.locator("#stage").screenshot(animations="disabled")
                        fingerprints.append(
                            _visual_fingerprint(screenshot, field=f"{viewport['id']} {label} frame")
                        )
                        frame_results.append({"label": label, "frame_index": frame_index})
                        if output_root is not None:
                            relative = f"presentation/stage-{viewport['id']}-{label}.png"
                            target = ensure_contained_path(output_root, output_root / relative)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(screenshot)
                            artifact_names.append(relative)
                    if probe_frames[0] != probe_frames[1] and len(set(fingerprints)) != 2:
                        raise StageRuntimeError(
                            f"{viewport['id']} Game Stage did not visibly change between frames"
                        )

                    stage_frame = next(
                        (frame for frame in page.frames if "/stage/" in frame.url), None
                    )
                    if stage_frame is None:
                        raise StageRuntimeError("Game Stage iframe did not load")
                    sandbox = page.locator("#stage").get_attribute("sandbox")
                    if sandbox != "allow-scripts":
                        raise StageIsolationError(
                            "Game Stage iframe sandbox grants capabilities beyond scripts"
                        )
                    dimensions = stage_frame.evaluate("""() => ({
                          width: document.documentElement.clientWidth,
                          height: document.documentElement.clientHeight,
                          scrollWidth: document.documentElement.scrollWidth,
                          scrollHeight: document.documentElement.scrollHeight
                        })""")
                    if (
                        dimensions["scrollWidth"] > dimensions["width"] + 1
                        or dimensions["scrollHeight"] > dimensions["height"] + 1
                    ):
                        raise StageRuntimeError(
                            f"{viewport['id']} Game Stage overflows its viewport"
                        )
                    probe_errors = page.evaluate("window.__agentdeckProbe.errors")
                    if blocked:
                        raise StageIsolationError(
                            f"Game Stage attempted external request: {blocked[0]}"
                        )
                    csp_errors = [
                        message
                        for message in console_errors
                        if "violates the following Content Security Policy" in message
                    ]
                    if csp_errors:
                        raise StageIsolationError(
                            "Game Stage attempted an external request or forbidden browser "
                            f"capability: {csp_errors[0]}"
                        )
                    if console_errors or page_errors or probe_errors:
                        problem = (console_errors + page_errors + probe_errors)[0]
                        raise StageRuntimeError(f"Game Stage browser error: {problem}")
                    results.append(
                        {
                            "id": viewport["id"],
                            "width": viewport["width"],
                            "height": viewport["height"],
                            "frames": frame_results,
                        }
                    )
                except PlaywrightError as exc:
                    if blocked:
                        raise StageIsolationError(
                            f"Game Stage attempted external request: {blocked[0]}"
                        ) from exc
                    raise StageRuntimeError(
                        f"Game Stage browser protocol timed out or failed: {exc}"
                    ) from exc
                finally:
                    context.close()
        finally:
            browser.close()
            playwright.stop()

    result = {
        "schema_version": "1.0",
        "protocol": STAGE_PROTOCOL,
        "match_id": match_id,
        "frame_count": len(frames),
        "sandbox": ["allow-scripts"],
        "viewports": results,
        "artifacts": artifact_names,
    }
    require_json_value(result, field="Game Stage certification")
    return result


__all__ = [
    "STAGE_PROTOCOL",
    "StageCertificationError",
    "StageIsolationError",
    "StageRuntimeError",
    "certify_game_stage",
]
