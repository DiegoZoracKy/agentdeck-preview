"""Public renderer symbols remain available to extension authors."""

from agentdeck import RenderResult, Renderer
from agentdeck.core.base import Renderer as CanonicalRenderer
from agentdeck.core.types import RenderResult as CanonicalRenderResult


def test_root_package_reexports_renderer_result_contract():
    assert RenderResult is CanonicalRenderResult
    assert Renderer is CanonicalRenderer
