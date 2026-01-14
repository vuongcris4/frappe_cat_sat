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
		
		# Calculate complete products using POOLED distribution
		# We aggregate ALL produced quantities from all orders into a single pool
		# Then attempting to "build" products sequentially until pool is exhausted.
		
		# 1. Build Global Produced Pool: (Steel Profile, Length) -> Total Produced
		global_produced_pool = defaultdict(int)
		for order_info in orders:
			order_doc = frappe.get_doc("Cutting Order", order_info.name)
			for item in order_doc.items:
				key = (order_info.steel_profile, item.length_mm)
				global_produced_pool[key] += item.produced_qty or 0

		# 2. Iterate Plan Items (Products) and calculate completion
		complete_products = []
		
		for plan_item in self.items:
			item_code = plan_item.item_code
			product_qty = plan_item.product_qty
			
			spec_name = frappe.db.get_value("Item", item_code, "cutting_specification")
			if not spec_name:
				continue
			
			spec = frappe.get_doc("Cutting Specification", spec_name)
			
			# Determine how many products we can make from the GLOBAL pool
			# This is tricky because multiple products might share the same profile/length resources.
			# Ideally we should allocate resources to products in order.
			# But for simplicity, assuming products use distinct specs OR we calculate "Potential Sets" 
			# However, if products share components, we must decrement the pool!
			
			# We will calculate strictly based on remaining pool
			
			product_complete_count = 0
			
			# Check requirements for ONE product unit
			# Map: (Profile, Length) -> Qty needed per product
			unit_reqs = defaultdict(int)
			for piece in spec.pieces:
				piece_qty = piece.piece_qty or 0
				for d in spec.details:
					if d.piece_name == piece.piece_name:
						# Key for pool
						p_key = (d.steel_profile, d.length_mm)
						# Qty segment per piece * pieces per product
						needed = (d.qty_segment_per_piece or 1) * piece_qty
						unit_reqs[p_key] += needed

			# Try to build products one by one (or calculate max possible)
			# Finding max possible is limited by the scarcest resource
			# But we must modify the global pool if we "consume" it for this product line
			# to avoid double counting if another item uses same resource.
			
			# Optimization: Find max possible for this line given the pool
			# Then Consume it?
			
			max_possible_sets = float('inf')
			
			for key, qty_per_product in unit_reqs.items():
				available = global_produced_pool.get(key, 0)
				if qty_per_product > 0:
					sets = available // qty_per_product
					max_possible_sets = min(max_possible_sets, sets)
				else:
					# No requirement for this key?
					pass
			
			if max_possible_sets == float('inf'):
				max_possible_sets = 0
				
			# Cap at required quantity
			sets_made = min(max_possible_sets, product_qty)
			
			# Decrement pool (Commit the resources to this product line)
			# This ensures next product in the loop doesn't use same pieces
			for key, qty_per_product in unit_reqs.items():
				used = sets_made * qty_per_product
				global_produced_pool[key] = max(0, global_produced_pool.get(key, 0) - used)

			# ... (sets calculation logic)
			
			# Snapshot the state of pieces for this product for reporting
			product_pieces = []
			for piece in spec.pieces:
				piece_qty = piece.piece_qty or 0
				p_name = piece.piece_name
				
				# Calculate total needed for this product line
				total_needed_for_product = product_qty * piece_qty
				
				# Calculate how many "sets" of this piece we effectively found
				# (This is approximate because a piece involves multiple segments)
				# But for reporting: "Required: 100, Ready: 50" (based on limiting segment)
				
				# Re-check availability for this specific piece in current pool state?
				# No, we already decremented pool!
				# Effectively "Allocated" = sets_made * piece_qty
				# But user wants to see "Why only 0 sets?" -> "Because Piece A is missing".
				# So we should show "Potential" based on pool state BEFORE decrement?
				
				# Let's show: Required vs Allocated (based on complete sets)
				# Or better: Show "Available pieces" based on current pool (BEFORE decrement would be better for diagnosis)
				
				# Simpler approach for now: Just show what was strictly allocated
				allocated_qty = sets_made * piece_qty
				
				product_pieces.append({
					"piece_name": p_name,
					"required": total_needed_for_product,
					"allocated": allocated_qty,
					"missing": total_needed_for_product - allocated_qty
				})

			complete_products.append({
				"item_code": item_code,
				"item_name": frappe.db.get_value("Item", item_code, "item_name"),
				"qty_required": product_qty,
				"qty_complete": sets_made,
				"remaining": max(0, product_qty - sets_made),
				"percent": round((sets_made / product_qty * 100) if product_qty > 0 else 0, 1),
				"pieces": product_pieces # Add detailed breakdown
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
