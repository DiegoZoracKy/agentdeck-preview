"""The Agentic Edge P1 pilot Assembly."""

from agentdeck import Assembly

from assembly_common import create_phase_assembly


def create_assembly() -> Assembly:
    return create_phase_assembly("P1")

