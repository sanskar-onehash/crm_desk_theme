from __future__ import annotations

import json
import re

import frappe
from frappe.model.document import Document
from frappe.utils import cint

from crm_desk_theme.services.cache import clear_theme_runtime_cache
from crm_desk_theme.services.compiler import compile_theme_css


TOKEN_NAME_PATTERN = re.compile(r"^--[a-z0-9-]+$")
LIGHT_VISUAL_TOKEN_FIELD_MAP = {
	"topbar_bg": "--cdt-topbar-bg",
	"sidebar_bg": "--cdt-sidebar-bg",
	"content_bg": "--cdt-content-bg",
	"card_bg": "--cdt-card-bg",
	"text_color": "--cdt-text-color",
	"heading_color": "--cdt-heading-color",
	"border_color": "--cdt-border-color",
	"link_color": "--cdt-link-color",
	"primary_accent": "--cdt-primary-accent",
	"button_bg": "--cdt-button-bg",
	"button_text_color": "--cdt-button-text-color",
	"scrollbar_thumb": "--cdt-scrollbar-thumb",
	"scrollbar_track": "--cdt-scrollbar-track",
	"font_family": "--cdt-font-family",
	"radius_md": "--cdt-radius-md",
}
DARK_VISUAL_TOKEN_FIELD_MAP = {
	"dark_topbar_bg": "--cdt-topbar-bg",
	"dark_sidebar_bg": "--cdt-sidebar-bg",
	"dark_content_bg": "--cdt-content-bg",
	"dark_card_bg": "--cdt-card-bg",
	"dark_text_color": "--cdt-text-color",
	"dark_heading_color": "--cdt-heading-color",
	"dark_border_color": "--cdt-border-color",
	"dark_link_color": "--cdt-link-color",
	"dark_primary_accent": "--cdt-primary-accent",
	"dark_button_bg": "--cdt-button-bg",
	"dark_button_text_color": "--cdt-button-text-color",
	"dark_scrollbar_thumb": "--cdt-scrollbar-thumb",
	"dark_scrollbar_track": "--cdt-scrollbar-track",
	"dark_font_family": "--cdt-font-family",
	"dark_radius_md": "--cdt-radius-md",
}


class DeskTheme(Document):
	def validate(self):
		self.theme_name = (self.theme_name or "").strip()
		self._normalise_status_flags()
		self._validate_shared_visual_fields()
		self._normalize_mode_scoped_tokens()
		self._sync_visual_fields_and_tokens()
		self._normalise_tokens()
		self._normalise_rules()
		self.generated_css = compile_theme_css(self)
		self.version = self._next_version()

	def on_update(self):
		self._clear_other_defaults()
		self._ensure_revision()
		if self.status == "Published" and self.enabled:
			clear_theme_runtime_cache()

	def get_snapshot_data(self) -> dict:
		return {
			"theme_name": self.theme_name,
			"enabled": bool(self.enabled),
			"is_default": bool(self.is_default),
			"status": self.status,
			"description": self.description,
			"allowed_users": [{"user": row.user} for row in self.allowed_users or [] if getattr(row, "user", None)],
			"base_preset": self.base_preset,
			"mode_strategy": self.mode_strategy,
			"default_mode": self.default_mode,
			"preview_mode": self.preview_mode,
			"allow_custom_css": bool(self.allow_custom_css),
			"allow_custom_js": bool(self.allow_custom_js),
			"custom_css": self.custom_css,
			"custom_js": self.custom_js,
			"generated_css": self.generated_css,
			"version": self.version,
			"tokens": [
				{
					"token_name": token.token_name,
					"token_value": token.token_value,
					"mode_scope": getattr(token, "mode_scope", "All"),
					"device_scope": token.device_scope,
					"semantic_area": token.semantic_area,
				}
				for token in self.tokens or []
			],
			"rules": [
				{
					"priority": rule.priority,
					"enabled": bool(rule.enabled),
					"match_type": rule.match_type,
					"match_value": rule.match_value,
					"mode_scope": getattr(rule, "mode_scope", "All"),
					"override_tokens": rule.override_tokens,
					"override_css": rule.override_css,
				}
				for rule in self.rules or []
			],
		}

	def _next_version(self) -> int:
		current_version = cint(self.version)
		if self.is_new():
			return current_version or 1

		return current_version + 1

	def _normalise_status_flags(self) -> None:
		self.editor_mode = (self.editor_mode or "Visual").strip() or "Visual"
		self.mode_strategy = (self.mode_strategy or "Shared").strip() or "Shared"
		self.default_mode = (self.default_mode or "Follow System").strip() or "Follow System"
		self.preview_mode = (self.preview_mode or "Light").strip() or "Light"

		mode_aliases = {
			"Single": "Shared",
			"Dual": "Light and Dark",
			"System": "Follow System",
		}
		self.mode_strategy = mode_aliases.get(self.mode_strategy, self.mode_strategy)
		self.default_mode = mode_aliases.get(self.default_mode, self.default_mode)

		if self.status == "Published":
			self.enabled = 1

		if self.status == "Archived":
			self.is_default = 0

	def _clear_other_defaults(self) -> None:
		if not self.is_default:
			return

		frappe.db.sql(
			"""
			update `tabDesk Theme`
			set is_default = 0
			where name != %s and ifnull(is_default, 0) = 1
			""",
			(self.name,),
		)

	def _ensure_revision(self) -> None:
		if self.status != "Published":
			return

		if not frappe.db.exists("DocType", "Desk Theme Revision"):
			return

		snapshot_json = json.dumps(self.get_snapshot_data(), indent=2, sort_keys=True)
		latest = frappe.get_all(
			"Desk Theme Revision",
			filters={"theme": self.name},
			fields=["name", "snapshot_json", "revision_no"],
			order_by="revision_no desc",
			limit=1,
		)
		if latest and latest[0].snapshot_json == snapshot_json:
			return

		revision_no = (latest[0].revision_no if latest else 0) + 1
		frappe.get_doc(
			{
				"doctype": "Desk Theme Revision",
				"theme": self.name,
				"revision_no": revision_no,
				"snapshot_json": snapshot_json,
				"published_by": frappe.session.user,
				"published_on": frappe.utils.now(),
			}
		).insert(ignore_permissions=True)

	def _normalise_tokens(self) -> None:
		for token in self.tokens or []:
			token_name = _normalise_token_name(token.token_name)
			token_value = (token.token_value or "").strip()

			if not token_name:
				frappe.throw("Desk Theme tokens require a token name.")

			if not TOKEN_NAME_PATTERN.match(token_name):
				frappe.throw(f"Invalid token name: {token_name}")

			if not token_value:
				frappe.throw(f"Desk Theme token {token_name} requires a value.")

			token.token_name = token_name
			token.token_value = token_value
			token.mode_scope = (getattr(token, "mode_scope", None) or "All").strip() or "All"
			token.device_scope = (token.device_scope or "All").strip() or "All"
			token.semantic_area = (token.semantic_area or "").strip()

	def _normalise_rules(self) -> None:
		for rule in self.rules or []:
			rule.priority = cint(rule.priority) or 100
			rule.match_value = (rule.match_value or "").strip()
			rule.mode_scope = (getattr(rule, "mode_scope", None) or "All").strip() or "All"
			rule.override_css = (rule.override_css or "").strip()

			if rule.override_tokens:
				try:
					parsed_tokens = json.loads(rule.override_tokens)
				except json.JSONDecodeError as exc:
					frappe.throw(
						f"Rule '{rule.match_type or 'Unknown'}' has invalid override token JSON: {exc.msg}"
					)

				rule.override_tokens = json.dumps(parsed_tokens, indent=2, sort_keys=True)

	def _validate_shared_visual_fields(self) -> None:
		if self.mode_strategy != "Shared":
			return

		for _, dark_field in _iter_visual_field_pairs():
			if getattr(self, dark_field, None):
				setattr(self, dark_field, "")

	def _sync_visual_fields_and_tokens(self) -> None:
		self._sync_visual_palette(LIGHT_VISUAL_TOKEN_FIELD_MAP, "Light")
		if self.mode_strategy != "Shared":
			self._sync_visual_palette(DARK_VISUAL_TOKEN_FIELD_MAP, "Dark")

	def _normalize_mode_scoped_tokens(self) -> None:
		tokens = list(self.tokens or [])
		if not tokens:
			return

		seen = set()
		deduped_tokens = []
		for token in tokens:
			token_name = (token.token_name or "").strip()
			mode_scope = (getattr(token, "mode_scope", None) or "All").strip() or "All"
			device_scope = (token.device_scope or "All").strip() or "All"
			key = (token_name, mode_scope, device_scope)
			if key in seen:
				continue
			seen.add(key)
			deduped_tokens.append(token)

		if self.mode_strategy == "Shared":
			for token in deduped_tokens:
				token.mode_scope = "All"
		elif self.mode_strategy == "Light Only":
			for token in deduped_tokens:
				if (getattr(token, "mode_scope", None) or "All") == "Dark":
					token.mode_scope = "Light"
				elif (getattr(token, "mode_scope", None) or "All") == "All":
					token.mode_scope = "Light"
		elif self.mode_strategy == "Dark Only":
			for token in deduped_tokens:
				if (getattr(token, "mode_scope", None) or "All") == "Light":
					token.mode_scope = "Dark"
				elif (getattr(token, "mode_scope", None) or "All") == "All":
					token.mode_scope = "Dark"

		self.set("tokens", deduped_tokens)

	def _sync_visual_palette(self, field_map: dict[str, str], mode_scope: str) -> None:
		tokens_by_key = {
			(
				(token.token_name or "").strip(),
				(getattr(token, "mode_scope", None) or "All").strip() or "All",
			): token
			for token in (self.tokens or [])
			if token.token_name
		}

		for fieldname, token_name in field_map.items():
			field_value = (getattr(self, fieldname, None) or "").strip()
			target_mode_scope = _get_target_mode_scope(self.mode_strategy, mode_scope)
			token = tokens_by_key.get((token_name, target_mode_scope))
			fallback_token = tokens_by_key.get((token_name, "All"))
			light_token = tokens_by_key.get((token_name, "Light"))
			dark_token = tokens_by_key.get((token_name, "Dark"))

			if field_value:
				target_token = token
				if target_mode_scope == "All":
					target_token = token or fallback_token or light_token
				elif target_mode_scope == "Light":
					target_token = token or fallback_token
				elif target_mode_scope == "Dark":
					target_token = token or (dark_token if mode_scope == "Dark" else None)
				if target_token:
					target_token.token_value = field_value
					target_token.mode_scope = target_mode_scope
					target_token.device_scope = target_token.device_scope or "All"
				else:
					self.append(
						"tokens",
						{
							"token_name": token_name,
							"token_value": field_value,
							"mode_scope": target_mode_scope,
						"device_scope": "All",
							"semantic_area": _default_semantic_area(token_name),
						},
					)
			elif self._remove_synced_visual_token(token_name, target_mode_scope):
				tokens_by_key = {
					(
						(existing_token.token_name or "").strip(),
						(getattr(existing_token, "mode_scope", None) or "All").strip() or "All",
					): existing_token
					for existing_token in (self.tokens or [])
					if existing_token.token_name
				}
			elif token and (token.device_scope or "All") == "All":
				if _can_sync_token_to_visual_field(fieldname, token.token_value):
					setattr(self, fieldname, token.token_value)
			elif target_mode_scope in {"All", "Light"} and fallback_token and (fallback_token.device_scope or "All") == "All":
				if _can_sync_token_to_visual_field(fieldname, fallback_token.token_value):
					setattr(self, fieldname, fallback_token.token_value)
			elif target_mode_scope == "Light" and light_token and (light_token.device_scope or "All") == "All":
				if _can_sync_token_to_visual_field(fieldname, light_token.token_value):
					setattr(self, fieldname, light_token.token_value)
			elif target_mode_scope == "Dark" and dark_token and (dark_token.device_scope or "All") == "All":
				if _can_sync_token_to_visual_field(fieldname, dark_token.token_value):
					setattr(self, fieldname, dark_token.token_value)
			elif target_mode_scope == "All" and light_token and (light_token.device_scope or "All") == "All":
				if _can_sync_token_to_visual_field(fieldname, light_token.token_value):
					setattr(self, fieldname, light_token.token_value)

	def _remove_synced_visual_token(self, token_name: str, mode_scope: str) -> bool:
		tokens = list(self.tokens or [])
		if not tokens:
			return False

		filtered_tokens = [
			token
			for token in tokens
			if not (
				(token.token_name or "").strip() == token_name
				and ((getattr(token, "mode_scope", None) or "All").strip() or "All") == mode_scope
				and (token.device_scope or "All").strip() == "All"
			)
		]
		if len(filtered_tokens) == len(tokens):
			return False

		self.set("tokens", filtered_tokens)
		return True


def _normalise_token_name(token_name: str | None) -> str:
	raw_name = (token_name or "").strip()
	if not raw_name:
		return ""

	if raw_name.startswith("--"):
		return raw_name

	raw_name = raw_name.lower()
	raw_name = re.sub(r"[^a-z0-9]+", "-", raw_name).strip("-")
	return f"--cdt-{raw_name}"


def _default_semantic_area(token_name: str) -> str:
	if "topbar" in token_name:
		return "Top Navbar"
	if "sidebar" in token_name:
		return "Sidebar"
	if "scrollbar" in token_name:
		return "Scrollbar"
	if "heading" in token_name:
		return "Typography"
	if "text" in token_name:
		return "Typography"
	if "link" in token_name:
		return "Links"
	if "border" in token_name:
		return "Borders"
	if "content" in token_name:
		return "App Shell"
	if "card" in token_name:
		return "Cards"
	if "accent" in token_name:
		return "Buttons"
	if "button" in token_name:
		return "Buttons"
	if "font" in token_name:
		return "Typography"
	if "radius" in token_name:
		return "Cards"
	return "App Shell"


def _get_target_mode_scope(mode_strategy: str, mode_scope: str) -> str:
	if mode_strategy == "Shared":
		return "All"
	if mode_strategy == "Light Only":
		return "Light"
	if mode_strategy == "Dark Only":
		return "Dark"
	if mode_strategy == "Light and Dark":
		return mode_scope
	return "All"


def _iter_visual_field_pairs():
	for light_field in LIGHT_VISUAL_TOKEN_FIELD_MAP:
		dark_field = f"dark_{light_field}"
		if dark_field in DARK_VISUAL_TOKEN_FIELD_MAP:
			yield light_field, dark_field


def _can_sync_token_to_visual_field(fieldname: str, token_value: str) -> bool:
	value = (token_value or "").strip()
	if not value:
		return False

	if fieldname in {"font_family", "dark_font_family"}:
		return value in {
			"Inter, sans-serif",
			"Roboto, sans-serif",
			"Lato, sans-serif",
			"Montserrat, sans-serif",
			"Open Sans, sans-serif",
			"Nunito, sans-serif",
		}

	if fieldname in {
		"topbar_bg",
		"sidebar_bg",
		"content_bg",
		"card_bg",
		"text_color",
		"heading_color",
		"border_color",
		"link_color",
		"primary_accent",
		"button_bg",
		"button_text_color",
		"scrollbar_thumb",
		"scrollbar_track",
		"dark_topbar_bg",
		"dark_sidebar_bg",
		"dark_content_bg",
		"dark_card_bg",
		"dark_text_color",
		"dark_heading_color",
		"dark_border_color",
		"dark_link_color",
		"dark_primary_accent",
		"dark_button_bg",
		"dark_button_text_color",
		"dark_scrollbar_thumb",
		"dark_scrollbar_track",
	}:
		return not value.startswith("var(")

	return True
