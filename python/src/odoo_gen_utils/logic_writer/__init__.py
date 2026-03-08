"""Logic writer package -- stub detection and context assembly.

Public API:
    detect_stubs: Scan module directory for TODO method stubs
    StubInfo: Frozen dataclass describing a detected stub
"""

from __future__ import annotations

from odoo_gen_utils.logic_writer.stub_detector import StubInfo, detect_stubs

__all__ = ["detect_stubs", "StubInfo"]
