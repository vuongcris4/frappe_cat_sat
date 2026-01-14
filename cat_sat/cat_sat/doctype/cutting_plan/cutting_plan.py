# Copyright (c) 2026, IEA and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint, flt
from cat_sat.services.cutting_plan_service import generate_requirements
from frappe.model.document import Document
from collections import defaultdict


class CuttingPlan(Document):
	def validate(self):
		if self.status != "Draft" and self.items:
			frappe.throw("Không được sửa danh sách thành phẩm khi kế hoạch đã xử lý")

	def before_save(self):
		if self.status == "Draft":
			generate_requirements(self)

	@frappe.whitelist()
	def get_progress_data(self):
		"""
		Calculate aggregate progress from all Cutting Orders linked to this plan.
		Returns data for dashboard display including complete products.
		"""
		# Find all Cutting Orders for this plan
		orders = frappe.get_all(
			"Cutting Order",
			filters={"cutting_plan": self.name},
			fields=["name", "steel_profile", "status", "completion_percent", "cutting_specification"]
		)
		
		if not orders:
			return None
		
		# Aggregate segment progress across all orders
		segment_progress = defaultdict(lambda: {"required": 0, "produced": 0, "segment_name": ""})
		
		for order_info in orders:
			order = frappe.get_doc("Cutting Order", order_info.name)
			for item in order.items:
				key = (order_info.steel_profile, item.length_mm)
				segment_progress[key]["required"] += item.qty
				segment_progress[key]["produced"] += item.produced_qty or 0
				segment_progress[key]["segment_name"] = item.segment_name or f"{item.length_mm}mm"
				segment_progress[key]["steel_profile"] = order_info.steel_profile
		
		# Calculate sync data for each specification
		sync_data = []
		specs_seen = set()
		for order_info in orders:
			if order_info.cutting_specification and order_info.cutting_specification not in specs_seen:
				specs_seen.add(order_info.cutting_specification)
				order = frappe.get_doc("Cutting Order", order_info.name)
				sync = order.get_sync_data()
				if sync:
					sync_data.append(sync)
		
		# Calculate complete products for each Item in plan
		complete_products = []
		for plan_item in self.items:
			item_code = plan_item.item_code
			product_qty = plan_item.product_qty
			
			# Get cutting specification for this item
			spec_name = frappe.db.get_value("Item", item_code, "cutting_specification")
			if not spec_name:
				continue
			
			spec = frappe.get_doc("Cutting Specification", spec_name)
			
			# Calculate how many complete products can be made
			# = min(complete_pieces / piece_qty for each piece)
			min_complete = float('inf')
			
			for piece in spec.pieces:
				piece_name = piece.piece_name
				piece_qty = piece.piece_qty or 1  # How many of this piece per product
				
				# Find how many of this piece are complete
				complete_pieces = 0
				for sync in sync_data:
					if sync.get("spec_name") == spec_name:
						for p in sync.get("pieces", []):
							if p.get("piece_name") == piece_name:
								complete_pieces = p.get("complete_pieces", 0)
								break
				
				# How many products can this piece support?
				can_make = complete_pieces // piece_qty if piece_qty > 0 else 0
				min_complete = min(min_complete, can_make)
			
			if min_complete == float('inf'):
				min_complete = 0
			
			complete_products.append({
				"item_code": item_code,
				"item_name": frappe.db.get_value("Item", item_code, "item_name"),
				"qty_required": product_qty,
				"qty_complete": min_complete,
				"remaining": max(0, product_qty - min_complete),
				"percent": round((min_complete / product_qty * 100) if product_qty > 0 else 0, 1)
			})
		
		# Calculate overall completion
		total_required = sum(s["required"] for s in segment_progress.values())
		total_produced = sum(s["produced"] for s in segment_progress.values())
		overall_percent = (total_produced / total_required * 100) if total_required > 0 else 0
		
		# Prepare segment list for display
		segments_list = []
		for (profile, length), data in sorted(segment_progress.items()):
			remaining = data["required"] - data["produced"]
			segments_list.append({
				"steel_profile": profile,
				"segment_name": data["segment_name"],
				"length_mm": length,
				"required": data["required"],
				"produced": data["produced"],
				"remaining": remaining,
				"percent": round((data["produced"] / data["required"] * 100) if data["required"] > 0 else 0, 1)
			})
		
		return {
			"orders": orders,
			"segments": segments_list,
			"sync_data": sync_data,
			"complete_products": complete_products,
			"summary": {
				"total_orders": len(orders),
				"total_required": total_required,
				"total_produced": total_produced,
				"overall_percent": round(overall_percent, 1)
			}
		}
