"""The Agentic Edge P0 no-provider preflight Assembly."""

from agentdeck import Assembly

from assembly_common import create_phase_assembly


def create_assembly() -> Assembly:
    return create_phase_assembly("P0")

