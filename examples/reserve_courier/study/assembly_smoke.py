from agentdeck import Assembly
from assembly_common import MODELS, make_run


def create_assembly():
    return Assembly(
        tuple(
            make_run(
                f"{model}-{advice}-{treatment}",
                model=provider_model,
                advice=advice,
                treatment=treatment,
                matches=1,
            )
            for model, provider_model in MODELS.items()
            for advice in ("none", "misleading")
            for treatment in ("action", "rationale")
        )
    )
