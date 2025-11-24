#!/usr/bin/env python3
"""
Bundle all AgentDeck specs into a single file for AI assistant knowledge bases.

Usage:
    python scripts/bundle_specs.py
    python scripts/bundle_specs.py --output custom_path.md

Output:
    specs/SPECS_BUNDLE.md (default)
"""

import argparse
from pathlib import Path
from datetime import datetime


def bundle_specs(output_path: Path) -> None:
    """Concatenate all spec files into a single markdown file."""
    specs_dir = Path(__file__).parent.parent / "specs"

    # Get all spec files, SPEC.md first, then alphabetically
    spec_files = sorted(specs_dir.glob("SPEC-*.md"))
    main_spec = specs_dir / "SPEC.md"

    if main_spec.exists():
        spec_files = [main_spec] + [f for f in spec_files if f != main_spec]

    # Bundle content
    content_parts = [
        "# AgentDeck Specifications Bundle",
        "",
        f"> Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> Source: {len(spec_files)} spec files",
        "> Purpose: Knowledge base for AI assistants (GPT, Gemini Gems)",
        "",
        "---",
        "",
    ]

    # Map spec files to descriptive section names
    spec_sections = {
        "SPEC.md": "Overview & Architecture",
        "SPEC-AGENTDECK.md": "AgentDeck Facade",
        "SPEC-CONSOLE.md": "Console",
        "SPEC-CONTROLLER.md": "Controller",
        "SPEC-GAME.md": "Game Interface",
        "SPEC-PLAYER.md": "Player Interface",
        "SPEC-RECORDER.md": "Recorder",
        "SPEC-RENDERER.md": "Renderer",
        "SPEC-SPECTATOR.md": "Spectators",
    }

    for spec_file in spec_files:
        if spec_file.name.startswith("_"):  # Skip templates
            continue

        content = spec_file.read_text(encoding="utf-8")
        section_name = spec_sections.get(spec_file.name, spec_file.stem)

        content_parts.extend([
            f"# {section_name} — {spec_file.name}",
            "",
            content,
            "",
            "---",
            "",
        ])

    # Write bundle
    output_path.write_text("\n".join(content_parts), encoding="utf-8")

    # Stats
    total_lines = sum(1 for _ in output_path.read_text().splitlines())
    total_size = output_path.stat().st_size / 1024

    print(f"✓ Bundled {len(spec_files)} specs into {output_path}")
    print(f"  Lines: {total_lines:,}")
    print(f"  Size: {total_size:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="Bundle specs for AI assistants")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path(__file__).parent.parent / "specs" / "SPECS_BUNDLE.md",
        help="Output file path (default: specs/SPECS_BUNDLE.md)"
    )
    args = parser.parse_args()

    bundle_specs(args.output)


if __name__ == "__main__":
    main()
