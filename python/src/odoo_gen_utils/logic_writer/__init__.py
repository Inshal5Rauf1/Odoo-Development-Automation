"""Logic writer package -- stub detection and context assembly.

Public API:
    detect_stubs: Scan module directory for TODO method stubs
    StubInfo: Frozen dataclass describing a detected stub
    build_stub_context: Assemble per-stub context from spec + registry
    StubContext: Frozen dataclass describing assembled context
"""

from __future__ import annotations

from odoo_gen_utils.logic_writer.context_builder import (
    StubContext,
    build_stub_context,
)
from odoo_gen_utils.logic_writer.stub_detector import StubInfo, detect_stubs

__all__ = ["build_stub_context", "detect_stubs", "StubContext", "StubInfo"]
