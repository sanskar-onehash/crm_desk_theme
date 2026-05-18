from __future__ import annotations

import json

import frappe

from crm_desk_theme.services.compiler import compile_theme_css


@frappe.whitelist()
def preview_theme(doc: str | dict) -> dict:
	theme_doc = _coerce_theme_doc(doc)
	return {
		"generated_css": compile_theme_css(theme_doc),
		"preview_mode": theme_doc.get("preview_mode") or "Light",
		"snapshot_json": json.dumps(_build_snapshot(theme_doc), indent=2, sort_keys=True),
	}


@frappe.whitelist()
def publish_theme(name: str) -> dict:
	doc = frappe.get_doc("Desk Theme", name)
	doc.status = "Published"
	doc.enabled = 1
	doc.save()
	return {
		"name": doc.name,
		"status": doc.status,
		"version": doc.version,
	}


@frappe.whitelist()
def export_theme(name: str) -> dict:
	doc = frappe.get_doc("Desk Theme", name)
	return {
		"name": doc.name,
		"theme_name": doc.theme_name,
		"snapshot_json": json.dumps(doc.get_snapshot_data(), indent=2, sort_keys=True),
	}


@frappe.whitelist()
def import_theme_snapshot(name: str, snapshot_json: str) -> dict:
	doc = frappe.get_doc("Desk Theme", name)
	snapshot = _parse_snapshot_json(snapshot_json)
	_apply_snapshot_to_theme(doc, snapshot)
	doc.save()
	return {
		"name": doc.name,
		"status": doc.status,
		"version": doc.version,
	}


@frappe.whitelist()
def get_theme_revisions(name: str) -> list[dict]:
	return frappe.get_all(
		"Desk Theme Revision",
		filters={"theme": name},
		fields=["name", "revision_no", "published_by", "published_on"],
		order_by="revision_no desc",
	)


@frappe.whitelist()
def rollback_theme_to_revision(name: str, revision_name: str) -> dict:
	doc = frappe.get_doc("Desk Theme", name)
	revision = frappe.get_doc("Desk Theme Revision", revision_name)
	if revision.theme != doc.name:
		frappe.throw("Selected revision does not belong to this theme.")

	snapshot = _parse_snapshot_json(revision.snapshot_json)
	_apply_snapshot_to_theme(doc, snapshot)
	doc.save()
	return {
		"name": doc.name,
		"status": doc.status,
		"version": doc.version,
		"revision_name": revision.name,
		"revision_no": revision.revision_no,
	}


def _coerce_theme_doc(doc: str | dict):
	if isinstance(doc, str):
		doc = json.loads(doc)

	theme_doc = frappe.get_doc(doc)
	if theme_doc.doctype != "Desk Theme":
		frappe.throw("Preview payload must be a Desk Theme document.")

	theme_doc.validate()
	return theme_doc


def _parse_snapshot_json(snapshot_json: str) -> dict:
	try:
		snapshot = json.loads(snapshot_json)
	except json.JSONDecodeError as exc:
		frappe.throw(f"Invalid snapshot JSON: {exc.msg}")

	if not isinstance(snapshot, dict):
		frappe.throw("Theme snapshot JSON must be an object.")

	return snapshot


def _apply_snapshot_to_theme(doc, snapshot: dict) -> None:
	allowed_scalar_fields = [
		"theme_name",
		"enabled",
		"is_default",
		"status",
		"description",
		"base_preset",
		"mode_strategy",
		"default_mode",
		"preview_mode",
		"allow_custom_css",
		"allow_custom_js",
		"custom_css",
		"custom_js",
	]

	for fieldname in allowed_scalar_fields:
		if fieldname in snapshot:
			setattr(doc, fieldname, snapshot.get(fieldname))

	doc.set("allowed_users", [])
	for row in snapshot.get("allowed_users", []) or []:
		if row.get("user"):
			doc.append("allowed_users", {"user": row.get("user")})

	doc.set("tokens", [])
	for token in snapshot.get("tokens", []) or []:
		doc.append(
			"tokens",
			{
				"token_name": token.get("token_name"),
				"token_value": token.get("token_value"),
				"mode_scope": token.get("mode_scope") or "All",
				"device_scope": token.get("device_scope") or "All",
				"semantic_area": token.get("semantic_area"),
			},
		)

	doc.set("rules", [])
	for rule in snapshot.get("rules", []) or []:
		doc.append(
			"rules",
			{
				"priority": rule.get("priority"),
				"enabled": rule.get("enabled"),
				"match_type": rule.get("match_type"),
				"match_value": rule.get("match_value"),
				"mode_scope": rule.get("mode_scope") or "All",
				"override_tokens": rule.get("override_tokens"),
				"override_css": rule.get("override_css"),
			},
		)


def _build_snapshot(theme_doc) -> dict:
	return {
		"theme_name": theme_doc.get("theme_name"),
		"enabled": bool(theme_doc.get("enabled")),
		"is_default": bool(theme_doc.get("is_default")),
		"status": theme_doc.get("status"),
		"description": theme_doc.get("description"),
		"allowed_users": [{"user": row.get("user")} for row in theme_doc.get("allowed_users", []) or [] if row.get("user")],
		"base_preset": theme_doc.get("base_preset"),
		"mode_strategy": theme_doc.get("mode_strategy"),
		"default_mode": theme_doc.get("default_mode"),
		"preview_mode": theme_doc.get("preview_mode"),
		"allow_custom_css": bool(theme_doc.get("allow_custom_css")),
		"allow_custom_js": bool(theme_doc.get("allow_custom_js")),
		"custom_css": theme_doc.get("custom_css"),
		"custom_js": theme_doc.get("custom_js"),
		"generated_css": compile_theme_css(theme_doc),
		"tokens": [
			{
				"token_name": token.get("token_name"),
				"token_value": token.get("token_value"),
				"mode_scope": token.get("mode_scope"),
				"device_scope": token.get("device_scope"),
				"semantic_area": token.get("semantic_area"),
			}
			for token in theme_doc.tokens
		],
		"rules": [
			{
				"priority": rule.get("priority"),
				"enabled": bool(rule.get("enabled")),
				"match_type": rule.get("match_type"),
				"match_value": rule.get("match_value"),
				"mode_scope": rule.get("mode_scope"),
				"override_tokens": rule.get("override_tokens"),
				"override_css": rule.get("override_css"),
			}
			for rule in theme_doc.rules
		],
	}
