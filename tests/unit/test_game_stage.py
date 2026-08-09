"""Direct invariant tests for the portable Game Stage contract."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from agentdeck.instruments import certify_instrument, validate_instrument

FIXTURE = Path(__file__).parents[1] / "fixtures" / "instruments" / "number_duel"


def _stage_html(*, body: str = "", style: str = "", before_ready: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
    body {{ display: grid; place-items: center; background: #07110f; color: #f7f4e8; }}
    main {{ width: min(92vw, 900px); padding: 32px; border: 2px solid #8de11f; }}
    h1 {{ margin: 0 0 16px; color: #8de11f; font: 700 28px sans-serif; }}
    pre {{ white-space: pre-wrap; font: 16px/1.5 monospace; }}
    {style}
  </style>
</head>
<body>
  <main><h1>NUMBER DUEL</h1><pre id="frame">WAITING FOR MATCH</pre>{body}</main>
  <script>
    (() => {{
      const protocol = "agentdeck-stage/1.0";
      const send = payload => parent.postMessage({{protocol, ...payload}}, "*");
      let surface = null;
      const render = (frame, frameIndex) => {{
        document.querySelector("#frame").textContent = JSON.stringify({{
          turn: frame.turn,
          player: frame.player,
          before: frame.state_before,
          after: frame.state_after
        }}, null, 2);
        send({{type: "agentdeck:stage-rendered", frame_index: frameIndex}});
      }};
      addEventListener("message", event => {{
        const message = event.data;
        if (!message || message.protocol !== protocol) return;
        if (message.type === "agentdeck:stage-load") {{
          const keys = Object.keys(message).sort().join(",");
          if (keys !== "match_surface,protocol,type") {{
            send({{type: "agentdeck:stage-error", message: "unexpected host authority"}});
            return;
          }}
          surface = message.match_surface;
          send({{
            type: "agentdeck:stage-loaded",
            match_id: surface.match.match_id,
            frame_count: surface.frames.length
          }});
        }} else if (message.type === "agentdeck:stage-render") {{
          if (!surface || JSON.stringify(surface.frames[message.frame_index]) !== JSON.stringify(message.frame)) {{
            send({{type: "agentdeck:stage-error", message: "frame is not from surface"}});
            return;
          }}
          render(message.frame, message.frame_index);
        }}
      }});
      {before_ready}
      send({{type: "agentdeck:stage-ready"}});
    }})();
  </script>
</body>
</html>
"""


def _copy_stage_package(tmp_path: Path, *, html: str | None = None) -> Path:
    package = tmp_path / "number-duel-stage"
    shutil.copytree(FIXTURE, package)
    presentation = package / "presentation"
    presentation.mkdir()
    (presentation / "index.html").write_text(
        html if html is not None else _stage_html(), encoding="utf-8"
    )
    manifest_path = package / "instrument.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "1.1"
    manifest["presentation"]["viewer"] = "presentation/index.html"
    manifest["presentation"]["viewer_protocol"] = "agentdeck-stage/1.0"
    manifest["claims"]["requested"].append("stage_ready")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return package


def _check(report, check_id: str) -> dict:
    return next(check for check in report.to_dict()["checks"] if check["id"] == check_id)


def test_ip16_stg2_stage_declaration_is_contained_and_technology_neutral(
    tmp_path: Path,
) -> None:
    """IP16 STG2: a dependency-free DOM Stage satisfies the declarative contract."""
    report = validate_instrument(_copy_stage_package(tmp_path))
    assert report.valid, report.to_dict()
    assert report.requested_tiers[-1] == "stage_ready"


def test_ip16_stage_ready_rejects_viewer_outside_presentation(tmp_path: Path) -> None:
    """IP16: stage_ready cannot promote an arbitrary package-root browser file."""
    package = _copy_stage_package(tmp_path)
    outside = package / "viewer.html"
    outside.write_text((package / "presentation" / "index.html").read_text(), encoding="utf-8")
    manifest_path = package / "instrument.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["presentation"]["viewer"] = "viewer.html"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    report = validate_instrument(package)
    assert not report.valid
    assert "must resolve under presentation/" in _check(report, "IP3")["message"]


def test_ip17_ip18_stg1_stg3_stg5_stg6_stg7_stg8_browser_certification(
    tmp_path: Path,
) -> None:
    """IP17 IP18 STG1 STG3 STG5 STG6 STG7 STG8: certify the full browser boundary."""
    output = tmp_path / "output"
    report = certify_instrument(
        _copy_stage_package(tmp_path), trust_mode="trusted-local", output_dir=output
    )
    assert report.valid, report.to_dict()
    assert report.awarded_tiers == [
        "runnable",
        "evidence_ready",
        "presentable",
        "stage_ready",
    ]
    assert _check(report, "IP17")["status"] == "passed"
    runtime = _check(report, "IP18")
    assert runtime["status"] == "passed"
    assert runtime["details"]["sandbox"] == ["allow-scripts"]
    assert [item["id"] for item in runtime["details"]["viewports"]] == [
        "desktop",
        "mobile",
    ]
    assert (output / "presentation" / "stage-certification.json").is_file()
    for viewport in ("desktop", "mobile"):
        for frame in ("first", "last"):
            assert (output / "presentation" / f"stage-{viewport}-{frame}.png").is_file()


def test_ip17_stg4_external_network_attempt_fails_stage_only(tmp_path: Path) -> None:
    """IP17 STG4: an external request fails stage_ready without erasing lower tiers."""
    html = _stage_html(before_ready='fetch("https://example.invalid/asset.png").catch(() => {});')
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert report.awarded_tiers == ["runnable", "evidence_ready", "presentable"]
    assert _check(report, "IP17")["status"] == "failed"
    assert "external request" in _check(report, "IP17")["message"]


def test_ip18_stg6_wrong_protocol_acknowledgement_is_rejected(tmp_path: Path) -> None:
    """IP18 STG6: a Stage using the wrong protocol never receives capability."""
    html = _stage_html().replace(
        'const protocol = "agentdeck-stage/1.0";',
        'const protocol = "agentdeck-stage/9.9";',
    )
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert report.awarded_tiers == ["runnable", "evidence_ready", "presentable"]
    assert _check(report, "IP18")["status"] == "failed"
    assert "protocol" in _check(report, "IP18")["message"]


def test_ip18_stg7_mobile_document_overflow_is_rejected(tmp_path: Path) -> None:
    """IP18 STG7: responsive certification rejects document overflow."""
    html = _stage_html(style="body { min-width: 700px; }")
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert _check(report, "IP18")["status"] == "failed"
    assert "mobile Game Stage overflows" in _check(report, "IP18")["message"]


def test_ip18_stg8_blank_visual_output_is_rejected(tmp_path: Path) -> None:
    """IP18 STG8: protocol success cannot substitute for visible frame output."""
    html = _stage_html(style="main { display: none; }")
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert report.awarded_tiers == ["runnable", "evidence_ready", "presentable"]
    assert _check(report, "IP18")["status"] == "failed"
    assert "blank visual output" in _check(report, "IP18")["message"]


def test_ip18_stg8_static_visual_output_is_rejected_for_distinct_frames(
    tmp_path: Path,
) -> None:
    """IP18 STG8: a static facade cannot claim to project distinct frames."""
    html = _stage_html().replace(
        'document.querySelector("#frame").textContent = JSON.stringify({\n'
        "          turn: frame.turn,\n"
        "          player: frame.player,\n"
        "          before: frame.state_before,\n"
        "          after: frame.state_after\n"
        "        }, null, 2);",
        'document.querySelector("#frame").textContent = "STATIC";',
    )
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert _check(report, "IP18")["status"] == "failed"
    assert "did not visibly change" in _check(report, "IP18")["message"]
