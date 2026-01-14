# Copyright (c) 2026, IEA and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CuttingSettings(Document):
	pass


def get_cutting_settings():
	"""Get Cutting Settings singleton document"""
	return frappe.get_single("Cutting Settings")


def get_max_waste_percent():
	"""Get max waste percentage from settings"""
	settings = get_cutting_settings()
	return settings.max_waste_percent or 1


def get_max_manual_input_count():
	"""Get max manual input count from settings"""
	settings = get_cutting_settings()
	return settings.max_manual_input_count or 5
