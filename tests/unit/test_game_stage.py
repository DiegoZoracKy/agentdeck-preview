"""Direct invariant tests for the portable Game Stage contract."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from agentdeck.instruments import certify_instrument, validate_instrument
from agentdeck.instruments.stage import _stage_context

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
      const protocol = "agentdeck-stage/1.1";
      const send = payload => parent.postMessage({{protocol, ...payload}}, "*");
      let context = null;
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
          if (keys !== "context,protocol,type") {{
            send({{type: "agentdeck:stage-error", message: "unexpected host authority"}});
            return;
          }}
          context = message.context;
          const contextKeys = Object.keys(context).sort().join(",");
          const matchKeys = Object.keys(context.match).sort().join(",");
          if (contextKeys !== "frame_count,match,players,schema_version" ||
              matchKeys !== "game,match_id,seed" ||
              context.players.some(player => Object.keys(player).sort().join(",") !== "model,name")) {{
            send({{type: "agentdeck:stage-error", message: "future match data exposed"}});
            return;
          }}
          send({{
            type: "agentdeck:stage-loaded",
            match_id: context.match.match_id,
            frame_count: context.frame_count
          }});
        }} else if (message.type === "agentdeck:stage-render") {{
          const keys = Object.keys(message).sort().join(",");
          if (!context || keys !== "frame,frame_index,protocol,type" ||
              message.frame_index < 0 || message.frame_index >= context.frame_count ||
              !message.frame || typeof message.frame !== "object") {{
            send({{type: "agentdeck:stage-error", message: "invalid current frame"}});
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
    manifest["presentation"]["viewer_protocol"] = "agentdeck-stage/1.1"
    manifest["claims"]["requested"].append("stage_ready")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return package


def _check(report, check_id: str) -> dict:
    return next(check for check in report.to_dict()["checks"] if check["id"] == check_id)


def test_ip17_stg3_initial_context_excludes_future_match_data() -> None:
    """IP17 STG3: initial Stage authority contains only pre-match identity."""
    surface = {
        "match": {
            "match_id": "match-1",
            "game": "NumberDuel",
            "seed": 42,
            "winner": "Alpha",
            "final_state": {"score": 3},
        },
        "players": [
            {"name": "Alpha", "model": "mock-a", "total_cost": 9.99},
            {"name": "Beta", "model": "mock-b", "conclusion": "I lost"},
        ],
        "frames": [{"phase_index": 0}, {"phase_index": 1}],
        "conclusions": [{"player": "Alpha", "text": "I won"}],
        "economics": {"total_cost": 9.99},
    }

    assert _stage_context(surface) == {
        "schema_version": "1.0",
        "match": {"match_id": "match-1", "game": "NumberDuel", "seed": 42},
        "players": [
            {"name": "Alpha", "model": "mock-a"},
            {"name": "Beta", "model": "mock-b"},
        ],
        "frame_count": 2,
    }


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


def test_ip16_stage_ready_rejects_superseded_protocol(tmp_path: Path) -> None:
    """IP16: stage_ready rejects the future-exposing protocol 1.0 contract."""
    package = _copy_stage_package(tmp_path)
    manifest_path = package / "instrument.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["presentation"]["viewer_protocol"] = "agentdeck-stage/1.0"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    report = validate_instrument(package)

    assert not report.valid
    assert "must be 'agentdeck-stage/1.1'" in _check(report, "IP3")["message"]


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
    stage_report_path = output / "presentation" / "stage-certification.json"
    assert stage_report_path.is_file()
    stage_report = yaml.safe_load(stage_report_path.read_text(encoding="utf-8"))
    assert all(
        viewport["rendered_frame_count"] == stage_report["frame_count"]
        for viewport in stage_report["viewports"]
    )
    assert all(
        viewport["visual_frame_count"] == stage_report["frame_count"]
        for viewport in stage_report["viewports"]
    )
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
        'const protocol = "agentdeck-stage/1.1";',
        'const protocol = "agentdeck-stage/9.9";',
    )
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert report.awarded_tiers == ["runnable", "evidence_ready", "presentable"]
    assert _check(report, "IP18")["status"] == "failed"
    assert "protocol" in _check(report, "IP18")["message"]


def test_ip18_stg6_middle_frame_failure_is_rejected(tmp_path: Path) -> None:
    """IP18 STG6: first/last success cannot hide an unrenderable middle frame."""
    html = _stage_html().replace(
        "const render = (frame, frameIndex) => {",
        "const render = (frame, frameIndex) => {\n"
        "        if (frameIndex === 1) {\n"
        '          send({type: "agentdeck:stage-error", message: "middle frame failed"});\n'
        "          return;\n"
        "        }",
    )
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert _check(report, "IP18")["status"] == "failed"
    assert "middle frame failed" in _check(report, "IP18")["message"]


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


def test_ip18_stg8_blank_intermediate_frame_is_rejected(tmp_path: Path) -> None:
    """IP18 STG8: visible boundaries cannot hide a blank intermediate frame."""
    html = _stage_html().replace(
        "const render = (frame, frameIndex) => {",
        "const render = (frame, frameIndex) => {\n"
        "        document.querySelector('main').style.display = "
        "frameIndex === 1 ? 'none' : 'block';",
    )
    report = certify_instrument(
        _copy_stage_package(tmp_path, html=html), trust_mode="trusted-local"
    )
    assert not report.valid
    assert report.awarded_tiers == ["runnable", "evidence_ready", "presentable"]
    assert _check(report, "IP18")["status"] == "failed"
    assert "mobile frame 1 produced blank visual output" in _check(report, "IP18")["message"] or (
        "desktop frame 1 produced blank visual output" in _check(report, "IP18")["message"]
    )


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
