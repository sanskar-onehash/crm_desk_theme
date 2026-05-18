from __future__ import annotations

import frappe


TRUSTED_THEME_ROLE = "System Manager"


def get_runtime_permissions(user: str | None = None) -> dict[str, bool]:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	can_manage_themes = TRUSTED_THEME_ROLE in roles

	return {
		"can_manage_themes": can_manage_themes,
		"can_use_custom_css": can_manage_themes,
		"can_use_custom_js": False,
	}
