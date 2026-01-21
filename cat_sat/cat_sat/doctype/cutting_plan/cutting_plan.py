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
			
			# Use factory_code fallback for SKU items
			from cat_sat.services.cutting_plan_service import get_cutting_spec_for_item
			spec_name = get_cutting_spec_for_item(item_code)
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
			
			# Build piece requirements from details (grouped by bom_item -> piece_name)
			# Each unique bom_item represents a "piece type"
			piece_info = {}  # piece_name -> {"qty": piece_qty, "segments": [...]}
			piece_name_cache = {}  # bom_item -> piece_name (cache for efficiency)
			
			for d in spec.details:
				bom_item = (d.bom_item or "").strip()
				if not bom_item:
					continue
				
				# Get piece_name from Item's custom field (with cache)
				if bom_item not in piece_name_cache:
					item_piece_name = frappe.db.get_value("Item", bom_item, "piece_name")
					# Just use the short name (e.g., "Khung tựa đôi")
					piece_name_cache[bom_item] = item_piece_name or bom_item
				
				p_name = piece_name_cache[bom_item]
				
				if p_name not in piece_info:
					# Get piece_qty from hardcoded mapping for I3/I5 products
					piece_qty_map = {
						"PHOI-I5.1.1": 1, "PHOI-I5.1.2": 1, "PHOI-I5.1.3": 1, "PHOI-I5.1.4": 1,
						"PHOI-I5.2.1": 2, "PHOI-I5.2.2": 2, "PHOI-I5.2.3": 2, "PHOI-I5.2.4": 2,
						"PHOI-I5.3.1": 1, "PHOI-I5.3.2": 2,
						"PHOI-I3.1.1": 2, "PHOI-I3.1.2": 2, "PHOI-I3.1.3": 2, "PHOI-I3.1.4": 2,
						"PHOI-I3.2.1": 1, "PHOI-I3.2.2": 2, "PHOI-I3.2.3": 2,
					}
					piece_qty = piece_qty_map.get(bom_item, 1)
					piece_info[p_name] = {
						"qty": piece_qty,
						"bom_item": bom_item,  # Store piece code for display
						"segments": []
					}
				piece_info[p_name]["segments"].append({
					"profile": d.steel_profile,
					"length": d.length_mm,
					"qty_per_unit": getattr(d, 'qty_per_unit', 1) or 1
				})
			
			# Check requirements for ONE product unit
			# Map: (Profile, Length) -> Qty needed per product
			unit_reqs = defaultdict(int)
			for p_name, pdata in piece_info.items():
				piece_qty = pdata["qty"]
				for seg in pdata["segments"]:
					p_key = (seg["profile"], seg["length"])
					needed = seg["qty_per_unit"] * piece_qty
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

			# Snapshot the state of pieces for this product for reporting
			product_pieces = []
			for p_name, pdata in piece_info.items():
				piece_qty = pdata["qty"]
				
				# Calculate total needed for this product line
				total_needed_for_product = product_qty * piece_qty
				
				# Effectively "Allocated" = sets_made * piece_qty
				allocated_qty = sets_made * piece_qty
				
				product_pieces.append({
					"piece_code": pdata.get("bom_item", ""),  # PHOI code for display
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
		
		# Calculate Time Statistics from Cutting Production Log
		time_stats = self.calculate_time_statistics()
		
		return {
			"orders": orders,
			"segments": segments_list,
			"sync_data": sync_data,
			"complete_products": complete_products,
			"time_statistics": time_stats,
			"summary": {
				"total_orders": len(orders),
				"total_required": total_required,
				"total_produced": total_produced,
				"overall_percent": round(overall_percent, 1)
			}
		}
	
	def calculate_time_statistics(self):
		"""
		Calculate time statistics from Cutting Production Log entries.
		Returns detailed breakdown for dashboard display.
		"""
		from collections import defaultdict
		
		# Get all production logs for this plan
		logs = frappe.get_all(
			"Cutting Production Log",
			filters={"cutting_plan": self.name, "status": "Done"},
			fields=["cutting_order", "steel_profile", "pattern", "pattern_idx",
					"start_time", "end_time", "duration_seconds", "qty_cut",
					"machine_no", "laser_speed", "issue_note"]
		)
		
		if not logs:
			return None
		
		# Aggregate statistics
		total_duration = 0
		total_qty_cut = 0
		by_steel_profile = defaultdict(lambda: {"duration": 0, "qty": 0, "count": 0})
		by_machine = defaultdict(lambda: {"duration": 0, "qty": 0, "count": 0, "issues": 0})
		issues_list = []
		
		first_start = None
		last_end = None
		
		for log in logs:
			duration = flt(log.duration_seconds) or 0
			qty = cint(log.qty_cut) or 0
			
			total_duration += duration
			total_qty_cut += qty
			
			# By steel profile
			profile = log.steel_profile or "Unknown"
			by_steel_profile[profile]["duration"] += duration
			by_steel_profile[profile]["qty"] += qty
			by_steel_profile[profile]["count"] += 1
			
			# By machine
			machine = log.machine_no or "N/A"
			by_machine[machine]["duration"] += duration
			by_machine[machine]["qty"] += qty
			by_machine[machine]["count"] += 1
			if log.issue_note:
				by_machine[machine]["issues"] += 1
				issues_list.append({
					"machine": machine,
					"pattern": log.pattern,
					"note": log.issue_note
				})
			
			# Track first/last times
			if log.start_time:
				start = frappe.utils.get_datetime(log.start_time)
				if first_start is None or start < first_start:
					first_start = start
			if log.end_time:
				end = frappe.utils.get_datetime(log.end_time)
				if last_end is None or end > last_end:
					last_end = end
		
		# Format durations
		def format_duration(seconds):
			if seconds < 60:
				return f"{int(seconds)}s"
			elif seconds < 3600:
				return f"{int(seconds // 60)}m {int(seconds % 60)}s"
			else:
				hours = int(seconds // 3600)
				mins = int((seconds % 3600) // 60)
				return f"{hours}h {mins}m"
		
		# By steel profile stats
		profile_stats = []
		for profile, data in sorted(by_steel_profile.items()):
			avg_per_bar = data["duration"] / data["qty"] if data["qty"] > 0 else 0
			profile_stats.append({
				"profile": profile,
				"duration": format_duration(data["duration"]),
				"duration_seconds": data["duration"],
				"qty": data["qty"],
				"count": data["count"],
				"avg_per_bar": format_duration(avg_per_bar),
				"avg_seconds": avg_per_bar
			})
		
		# By machine stats
		machine_stats = []
		for machine, data in sorted(by_machine.items()):
			avg_per_bar = data["duration"] / data["qty"] if data["qty"] > 0 else 0
			machine_stats.append({
				"machine": machine,
				"duration": format_duration(data["duration"]),
				"duration_seconds": data["duration"],
				"qty": data["qty"],
				"issues": data["issues"],
				"avg_per_bar": format_duration(avg_per_bar),
				"avg_seconds": avg_per_bar
			})
		
		# Estimate remaining time
		remaining_qty = sum(s["remaining"] for s in self.get_segments_progress()) if hasattr(self, 'get_segments_progress') else 0
		avg_time_per_segment = total_duration / total_qty_cut if total_qty_cut > 0 else 0
		estimated_remaining = remaining_qty * avg_time_per_segment
		
		# Calculate vs target  
		target_status = None
		if self.target_date and last_end:
			target_dt = frappe.utils.get_datetime(self.target_date)
			if last_end < target_dt:
				diff = (target_dt - last_end).days
				target_status = {"status": "ahead", "days": diff}
			else:
				diff = (last_end - target_dt).days
				target_status = {"status": "behind", "days": diff}
		
		return {
			"total_duration": format_duration(total_duration),
			"total_duration_seconds": total_duration,
			"total_qty_cut": total_qty_cut,
			"log_count": len(logs),
			"avg_per_bar": format_duration(total_duration / total_qty_cut if total_qty_cut > 0 else 0),
			"first_start": str(first_start)[:16] if first_start else None,
			"last_end": str(last_end)[:16] if last_end else None,
			"estimated_remaining": format_duration(estimated_remaining),
			"by_profile": profile_stats,
			"by_machine": machine_stats,
			"issues": issues_list[:10],  # Limit to 10 most recent
			"target_status": target_status
		}

