# Copyright (c) 2026, IEA and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CuttingPiece(Document):
	def validate(self):
		# Tự động cắt bỏ khoảng trắng thừa (trim)
		if self.piece_name:
			self.piece_name = self.piece_name.strip()
