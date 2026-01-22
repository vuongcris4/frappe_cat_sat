# Copyright (c) 2026, IEA and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CuttingProductionLog(Document):
	def on_trash(self):
		"""Recalculate parent Cutting Order progress when log is deleted"""
		if self.cutting_order:
			# Queue recalculation to run after commit
			frappe.enqueue(
				"cat_sat.cat_sat.doctype.cutting_production_log.cutting_production_log.recalculate_order_progress",
				cutting_order=self.cutting_order,
				queue="short"
			)


def recalculate_order_progress(cutting_order):
	"""Recalculate Cutting Order progress after Production Log deletion"""
	try:
		doc = frappe.get_doc("Cutting Order", cutting_order)
		doc.update_overall_progress()
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to recalculate progress for {cutting_order}: {str(e)}")
