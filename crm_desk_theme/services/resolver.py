from __future__ import annotations

import json

import frappe
from frappe.defaults import get_user_default

from crm_desk_theme.services.permissions import get_runtime_permissions


def extend_bootinfo(bootinfo) -> None:
	try:
		bootinfo.desk_theme_manager = build_boot_payload()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Desk Theme Boot Payload Failure")
		bootinfo.desk_theme_manager = {
			"theme": None,
			"rules": [],
			"permissions": get_runtime_permissions(),
		}


def build_boot_payload(user: str | None = None) -> dict:
	user = user or frappe.session.user

	if not frappe.db.exists("DocType", "Desk Theme"):
		return {
			"theme": None,
			"rules": [],
			"permissions": get_runtime_permissions(user),
		}

	theme = get_active_theme(user)
	if not theme:
		return {
			"theme": None,
			"rules": [],
			"permissions": get_runtime_permissions(user),
		}

	serialized_theme = serialise_theme(theme)
	return {
		"active_mode": get_initial_active_mode(theme),
		"theme": serialized_theme,
		"rules": serialized_theme["rules"],
		"permissions": get_runtime_permissions(user),
	}


def get_initial_active_mode(theme) -> str | None:
	user_mode = get_user_mode_preference()
	if user_mode in {"Light", "Dark"}:
		return user_mode

	default_mode = (getattr(theme, "default_mode", None) or "Follow System").strip() or "Follow System"

	if default_mode in {"Light", "Dark"}:
		return default_mode

	return None


def get_user_mode_preference(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None

	try:
		desk_theme = frappe.db.get_value("User", user, "desk_theme")
	except Exception:
		return None

	if desk_theme in {"Light", "Dark"}:
		return desk_theme

	return None


def get_active_theme(user: str | None = None):
	assigned_theme = get_assigned_theme(user)
	if assigned_theme:
		return assigned_theme

	default_theme = _get_first_visible_theme(
		user=user,
		filters={"enabled": 1, "status": "Published", "is_default": 1},
		order_by="modified desc",
	)
	if default_theme:
		return default_theme

	fallback_theme = _get_first_visible_theme(
		user=user,
		filters={"enabled": 1, "status": "Published"},
		order_by="is_default desc, modified desc",
	)
	if fallback_theme:
		return fallback_theme

	return None


def get_assigned_theme(user: str | None = None):
	user = user or frappe.session.user
	if not frappe.db.exists("DocType", "Desk Theme Assignment"):
		return None

	user_company = get_user_default("Company", user)
	user_roles = set(frappe.get_roles(user))
	assignments = frappe.get_all(
		"Desk Theme Assignment",
		filters={"enabled": 1},
		fields=["name", "assignment_type", "theme", "priority", "role", "user", "company", "creation"],
		order_by="priority asc, creation asc",
	)

	matching_rows = []
	for assignment in assignments:
		if assignment.assignment_type == "User" and assignment.user == user:
			matching_rows.append((0, assignment))
		elif assignment.assignment_type == "Company" and assignment.company and assignment.company == user_company:
			matching_rows.append((1, assignment))
		elif assignment.assignment_type == "Role" and assignment.role in user_roles:
			matching_rows.append((2, assignment))
		elif assignment.assignment_type == "Global":
			matching_rows.append((3, assignment))

	if not matching_rows:
		return None

	matching_rows.sort(key=lambda row: (row[0], row[1].priority, row[1].creation))
	for _, assignment in matching_rows:
		theme_name = frappe.db.get_value(
			"Desk Theme",
			{"name": assignment.theme, "enabled": 1, "status": "Published"},
			"name",
		)
		if theme_name:
			theme = frappe.get_doc("Desk Theme", theme_name)
			if _theme_is_visible_to_user(theme, user):
				return theme

	return None


def _get_first_visible_theme(user: str | None, filters: dict, order_by: str):
	theme_rows = frappe.get_all("Desk Theme", filters=filters, fields=["name"], order_by=order_by)
	for row in theme_rows:
		theme = frappe.get_doc("Desk Theme", row.name)
		if _theme_is_visible_to_user(theme, user):
			return theme

	return None


def _theme_is_visible_to_user(theme, user: str | None) -> bool:
	allowed_users = {row.user for row in getattr(theme, "allowed_users", []) or [] if getattr(row, "user", None)}
	if not allowed_users:
		return True

	return (user or frappe.session.user) in allowed_users


def serialise_theme(theme) -> dict:
	tokens = []
	for token in getattr(theme, "tokens", []) or []:
		tokens.append(
			{
				"token_name": token.token_name,
				"token_value": token.token_value,
				"mode_scope": getattr(token, "mode_scope", "All") or "All",
				"device_scope": token.device_scope or "All",
				"semantic_area": token.semantic_area,
			}
		)

	rules = []
	for rule in getattr(theme, "rules", []) or []:
		rules.append(
			{
				"name": rule.name,
				"priority": rule.priority or 100,
				"enabled": bool(rule.enabled),
				"match_type": rule.match_type,
				"match_value": rule.match_value,
				"mode_scope": getattr(rule, "mode_scope", "All") or "All",
				"override_tokens": _parse_json(rule.override_tokens),
				"override_css": rule.override_css,
			}
		)

	return {
		"name": theme.name,
		"theme_name": theme.theme_name,
		"status": theme.status,
		"description": theme.description,
		"base_preset": theme.base_preset,
		"mode_strategy": theme.mode_strategy,
		"default_mode": theme.default_mode,
		"preview_mode": theme.preview_mode,
		"allow_custom_css": bool(theme.allow_custom_css),
		"allow_custom_js": bool(theme.allow_custom_js),
		"generated_css": theme.generated_css,
		"custom_js": None,
		"version": theme.version,
		"tokens": tokens,
		"rules": sorted(rules, key=lambda row: row["priority"]),
	}


def _parse_json(raw_value):
	if not raw_value:
		return {}

	if isinstance(raw_value, dict):
		return raw_value

	try:
		return json.loads(raw_value)
	except Exception:
		return {}
