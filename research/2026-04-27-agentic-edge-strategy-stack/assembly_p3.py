"""The Agentic Edge P3 supplemental Assembly."""

from agentdeck import Assembly

from assembly_common import create_phase_assembly


def create_assembly() -> Assembly:
    return create_phase_assembly("P3")

