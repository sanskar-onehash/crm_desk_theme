import frappe


DEFAULT_THEME_NAME = "Default Desk Theme"
LEGACY_DEFAULT_THEME_TOKENS = [
	{"token_name": "--cdt-topbar-bg", "token_value": "#ffffff"},
	{"token_name": "--cdt-sidebar-bg", "token_value": "#f5f7fa"},
	{"token_name": "--cdt-content-bg", "token_value": "#fdfdfd"},
	{"token_name": "--cdt-text-color", "token_value": "#1f2937"},
	{"token_name": "--cdt-heading-color", "token_value": "#111827"},
	{"token_name": "--cdt-border-color", "token_value": "#d0d7de"},
	{"token_name": "--cdt-link-color", "token_value": "#2563eb"},
	{"token_name": "--cdt-primary-accent", "token_value": "#2563eb"},
	{"token_name": "--cdt-scrollbar-thumb", "token_value": "#cbd5e1"},
	{"token_name": "--cdt-scrollbar-track", "token_value": "#e2e8f0"},
	{"token_name": "--cdt-font-family", "token_value": "Inter, sans-serif"},
	{"token_name": "--cdt-radius-md", "token_value": "0.5rem"},
]
DEFAULT_THEME_TOKENS = [
	{"token_name": "--cdt-topbar-bg", "token_value": "var(--navbar-bg)"},
	{"token_name": "--cdt-sidebar-bg", "token_value": "var(--bg-color)"},
	{"token_name": "--cdt-content-bg", "token_value": "var(--bg-color)"},
	{"token_name": "--cdt-text-color", "token_value": "var(--text-color)"},
	{"token_name": "--cdt-heading-color", "token_value": "var(--heading-color)"},
	{"token_name": "--cdt-border-color", "token_value": "var(--border-color)"},
	{"token_name": "--cdt-link-color", "token_value": "var(--text-color)"},
	{"token_name": "--cdt-primary-accent", "token_value": "var(--primary)"},
	{"token_name": "--cdt-scrollbar-thumb", "token_value": "var(--scrollbar-thumb-color)"},
	{"token_name": "--cdt-scrollbar-track", "token_value": "var(--scrollbar-track-color)"},
	{"token_name": "--cdt-font-family", "token_value": "var(--font-stack)"},
	{"token_name": "--cdt-radius-md", "token_value": "var(--border-radius-md)"},
]


def after_install():
	ensure_default_theme()


def ensure_default_theme():
	if not frappe.db.exists("DocType", "Desk Theme"):
		return

	if frappe.db.exists("Desk Theme", {"is_default": 1}):
		return

	doc = frappe.get_doc(
		{
			"doctype": "Desk Theme",
			"theme_name": DEFAULT_THEME_NAME,
			"enabled": 1,
			"is_default": 1,
			"status": "Published",
			"description": "Initial desk theme created during app install.",
			"tokens": DEFAULT_THEME_TOKENS,
		}
	)
	doc.insert(ignore_permissions=True)


def sync_default_theme_to_frappe_defaults():
	"""Keep the shipped default theme visually identical to stock Frappe."""
	if not frappe.db.exists("Desk Theme", DEFAULT_THEME_NAME):
		return

	doc = frappe.get_doc("Desk Theme", DEFAULT_THEME_NAME)
	if not _is_pristine_default_theme(doc):
		return

	doc.tokens = []
	for token in DEFAULT_THEME_TOKENS:
		doc.append("tokens", token)
	doc.save(ignore_permissions=True)


def _is_pristine_default_theme(doc) -> bool:
	if doc.name != DEFAULT_THEME_NAME:
		return False

	if not getattr(doc, "is_default", 0):
		return False

	current_tokens = {
		((row.token_name or "").strip(), (getattr(row, "mode_scope", None) or "All").strip() or "All"): (row.token_value or "").strip()
		for row in (doc.tokens or [])
	}
	expected_legacy_tokens = {
		(token["token_name"], "All"): token["token_value"] for token in LEGACY_DEFAULT_THEME_TOKENS
	}
	expected_current_tokens = {
		(token["token_name"], "All"): token["token_value"] for token in DEFAULT_THEME_TOKENS
	}

	return current_tokens == expected_legacy_tokens or current_tokens == expected_current_tokens
