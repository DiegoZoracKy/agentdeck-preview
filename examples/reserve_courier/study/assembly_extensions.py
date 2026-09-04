from agentdeck import Assembly
from assembly_common import make_run


def create_assembly():
    return Assembly(
        tuple(
            make_run(f"extension-{treatment}", treatment=treatment, matches=2, extension=True)
            for treatment in ("json", "rationale")
        )
    )
