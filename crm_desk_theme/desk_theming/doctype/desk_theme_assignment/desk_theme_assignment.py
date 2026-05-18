from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class DeskThemeAssignment(Document):
	def validate(self):
		self.priority = cint(self.priority) or 100
		self._normalise_reference_fields()
		self._validate_required_reference()

	def _normalise_reference_fields(self) -> None:
		self.role = (self.role or "").strip()
		self.user = (self.user or "").strip()
		self.company = (self.company or "").strip()

		if self.assignment_type != "Role":
			self.role = ""
		if self.assignment_type != "User":
			self.user = ""
		if self.assignment_type != "Company":
			self.company = ""

	def _validate_required_reference(self) -> None:
		if self.assignment_type == "Role" and not self.role:
			frappe.throw("Role assignments require a role.")
		if self.assignment_type == "User" and not self.user:
			frappe.throw("User assignments require a user.")
		if self.assignment_type == "Company" and not self.company:
			frappe.throw("Company assignments require a company.")
