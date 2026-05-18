from __future__ import annotations

import frappe


def clear_theme_runtime_cache(user: str | None = None) -> None:
	"""Invalidate boot/runtime cache after a theme change."""
	frappe.clear_cache(user=user)

