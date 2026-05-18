import frappe

from crm_desk_theme.install import sync_default_theme_to_frappe_defaults


def execute():
	if not frappe.db.exists("DocType", "Desk Theme"):
		return

	sync_default_theme_to_frappe_defaults()
