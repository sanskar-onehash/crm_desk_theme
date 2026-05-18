# Copyright (c) 2026, OneHash and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from crm_desk_theme.api.theme import preview_theme


class TestDeskTheme(FrappeTestCase):
	def test_clearing_shared_visual_color_removes_synced_token(self):
		doc = self._build_theme(
			mode_strategy="Shared",
			text_color="",
			tokens=[
				{
					"doctype": "Desk Theme Token",
					"token_name": "--cdt-text-color",
					"token_value": "#112233",
					"mode_scope": "All",
					"device_scope": "All",
				}
			],
		)

		doc.validate()

		self.assertEqual(doc.text_color, "")
		self.assertFalse(doc.tokens)

	def test_clearing_dark_visual_color_only_removes_dark_token(self):
		doc = self._build_theme(
			mode_strategy="Light and Dark",
			text_color="#112233",
			dark_text_color="",
			tokens=[
				{
					"doctype": "Desk Theme Token",
					"token_name": "--cdt-text-color",
					"token_value": "#112233",
					"mode_scope": "Light",
					"device_scope": "All",
				},
				{
					"doctype": "Desk Theme Token",
					"token_name": "--cdt-text-color",
					"token_value": "#445566",
					"mode_scope": "Dark",
					"device_scope": "All",
				},
			],
		)

		doc.validate()

		self.assertEqual(doc.text_color, "#112233")
		self.assertEqual(doc.dark_text_color, "")
		self.assertEqual(len(doc.tokens), 1)
		self.assertEqual(doc.tokens[0].mode_scope, "Light")
		self.assertEqual(doc.tokens[0].token_value, "#112233")

	def test_preview_uses_normalized_tokens_after_clearing_visual_color(self):
		preview = preview_theme(
			{
				"doctype": "Desk Theme",
				"theme_name": "Test Theme Preview",
				"status": "Draft",
				"mode_strategy": "Shared",
				"default_mode": "Follow System",
				"preview_mode": "Light",
				"editor_mode": "Visual",
				"text_color": "",
				"tokens": [
					{
						"doctype": "Desk Theme Token",
						"token_name": "--cdt-text-color",
						"token_value": "#112233",
						"mode_scope": "All",
						"device_scope": "All",
					}
				],
				"rules": [],
			}
		)

		self.assertNotIn("--cdt-text-color", preview["generated_css"])

	def _build_theme(self, **overrides):
		payload = {
			"doctype": "Desk Theme",
			"theme_name": "Test Theme Sync",
			"status": "Draft",
			"mode_strategy": "Shared",
			"default_mode": "Follow System",
			"preview_mode": "Light",
			"editor_mode": "Visual",
			"tokens": [],
			"rules": [],
		}
		payload.update(overrides)
		return frappe.get_doc(payload)
