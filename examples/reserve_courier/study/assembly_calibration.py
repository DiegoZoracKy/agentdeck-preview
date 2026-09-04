from agentdeck import Assembly
from assembly_common import make_run


def create_assembly():
    return Assembly(
        tuple(
            make_run(f"calibration-{policy}", policy=policy)
            for policy in ("optimal", "greedy", "conservative")
        )
    )
