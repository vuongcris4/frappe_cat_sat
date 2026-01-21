# apps/cat_sat/cat_sat/cat_sat/doctype/cutting_order/cutting_order.py
# Copyright (c) 2026, IEA and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class CuttingOrder(Document):
	def get_matrix_data(self):
		"""
		Returns data structure for Print Format Matrix
		"""
		if not self.optimization_result:
			return None

		# Build item name map: length -> segment_name (use flt for consistent keys)
		item_name_map = {}
		for item in self.items:
			item_name_map[flt(item.length_mm)] = item.segment_name or f"{item.length_mm}mm"

		unique_lengths = set()
		parsed_patterns = []

		for row in self.optimization_result:
			counts = {}
			# row.pattern looks like "2x2000 + 1x1500"
			if row.pattern:
				parts = row.pattern.split(" + ")
				for part in parts:
					if "x" in part:
						try:
							c, l = part.split("x")
							# Handle float lengths like "1162.2"
							l_float = flt(l)
							c_int = int(c)
							counts[l_float] = c_int
							unique_lengths.add(l_float)
						except ValueError:
							pass

			parsed_patterns.append(
				{
					"qty": row.qty,
					"cut_qty": row.cut_qty or 0,
					"waste": row.waste,
					"used_length": row.used_length,
					"counts": counts,
					"stt": row.idx,
				}
			)

		sorted_lengths = sorted(list(unique_lengths), reverse=True)

		# 2. Build Column Headers with segment names
		column_headers = []
		for l in sorted_lengths:
			name = item_name_map.get(l, f"{l}mm")
			column_headers.append({
				"length": l,
				"name": name,
				"full": f"{name} ({l}mm)"
			})

		# 3. Build Rows
		matrix_rows = []
		for idx, p in enumerate(parsed_patterns):
			row_data = {
				"stt": idx + 1,
				"qty": p["qty"],
				"waste": p["waste"],
				"cells": [],  # List of counts corresponding to sorted_lengths
			}
			for l in sorted_lengths:
				val = p["counts"].get(l, "")
				row_data["cells"].append(val if val else "")

			matrix_rows.append(row_data)

		# 4. Summary
		total_stock = sum(r.qty for r in self.optimization_result)
		total_waste_length = sum(r.waste * r.qty for r in self.optimization_result)

		# Calculate waste percentage
		total_meter_input = total_stock * self.stock_length / 1000.0
		waste_percent = 0
		if total_meter_input > 0:
			waste_percent = (total_waste_length / 1000.0) / total_meter_input * 100

		# 5. Items Summary (for "Tổng kết cắt" table)
		items_summary = []
		for item in self.items:
			items_summary.append({
				"segment_name": item.segment_name or f"Đoạn {item.length_mm}mm",
				"length_mm": item.length_mm,
				"qty_required": item.qty,
				"qty_produced": item.produced_qty or 0,
				"qty_remaining": item.qty - (item.produced_qty or 0),
			})

		return {
			"columns": sorted_lengths,
			"column_headers": column_headers,
			"rows": matrix_rows,
			"items_summary": items_summary,
			"summary": {
				"total_stock": total_stock,
				"total_waste_m": round(total_waste_length / 1000.0, 2),
				"waste_percent": round(waste_percent, 2),
			},
		}


	def get_sync_data(self):
		"""
		Returns data for synchronized cutting report.
		Calculates how many complete pieces can be assembled based on cut segments.
		"""
		if not self.cutting_specification:
			return None
		
		# Get the specification
		spec = frappe.get_doc("Cutting Specification", self.cutting_specification)
		
		# Build produced qty map: length_mm -> produced_qty
		produced_map = {}
		for item in self.items:
			produced_map[item.length_mm] = item.produced_qty or 0
		
		# Build required qty map: length_mm -> total required
		required_map = {}
		for item in self.items:
			required_map[item.length_mm] = item.qty
		
		# Calculate sync for each piece
		pieces_sync = []
		for piece in spec.pieces:
			piece_name = piece.piece_name
			piece_qty_required = piece.piece_qty  # Number of pieces needed
			
			# Find all segments for this piece
			segments = []
			min_complete = float('inf')
			
			for detail in spec.details:
				# Handle "piece_code - piece_name" format
				detail_piece = (detail.piece_name or "").strip()
				if " - " in detail_piece:
					detail_piece = detail_piece.split(" - ", 1)[1]
				if detail_piece == piece_name:
					length = cint(detail.length_mm)
					qty_per_piece = getattr(detail, 'qty_per_unit', None) or getattr(detail, 'qty_segment_per_piece', 1) or 1
					produced = produced_map.get(length, 0)
					required_total = required_map.get(length, 0)
					
					# How many complete pieces can we make from this segment type?
					can_make = produced // qty_per_piece if qty_per_piece > 0 else 0
					if can_make < min_complete:
						min_complete = can_make
					
					segments.append({
						"segment_name": detail.segment_name or f"{length}mm",
						"length_mm": length,
						"qty_per_piece": qty_per_piece,
						"produced": produced,
						"required": required_total,
						"can_make": can_make,
					})
			
			if min_complete == float('inf'):
				min_complete = 0
			
			pieces_sync.append({
				"piece_name": piece_name,
				"qty_required": piece_qty_required,
				"complete_pieces": min_complete,
				"remaining": max(0, piece_qty_required - min_complete),
				"percent": round((min_complete / piece_qty_required * 100) if piece_qty_required > 0 else 0, 1),
				"segments": segments,
			})
		
		return {
			"spec_name": spec.spec_name,
			"pieces": pieces_sync,
		}

	@frappe.whitelist()
	def update_pattern_progress(self, row_idx, action, session_qty=0, machine_no=None, laser_speed=None, issue_note=None):
		"""
		Handles the Start/Stop logic for a specific pattern row.
		Uses row_idx (1-indexed) for reliable row lookup.
		Creates/Updates Cutting Production Log for time tracking.
		"""
		# Reload doc from DB to ensure we have the correct Child Table rows
		doc = frappe.get_doc(self.doctype, self.name)

		# Lookup by idx (1-indexed, so subtract 1)
		row = None
		idx = cint(row_idx) - 1
		if 0 <= idx < len(doc.optimization_result):
			row = doc.optimization_result[idx]

		if not row:
			frappe.throw(f"Không tìm thấy mẫu cắt (row {row_idx}). Vui lòng tải lại trang.")

		now = frappe.utils.now_datetime()

		# Use frappe.db.set_value for robust updates on Submitted Docs
		if action == "Start":
			if row.status == "In Progress":
				frappe.msgprint("Mẫu này đang chạy rồi.")
				return

			# Direct DB update
			frappe.db.set_value(
				"Cutting Pattern", row.name, {"status": "In Progress", "last_start_time": now}
			)
			
			# Create Production Log entry
			log = frappe.new_doc("Cutting Production Log")
			log.cutting_order = self.name
			log.cutting_plan = self.cutting_plan
			log.pattern_idx = row.idx
			log.steel_profile = self.steel_profile
			log.stock_length = self.stock_length
			log.pattern = row.pattern
			log.start_time = now
			log.status = "Running"
			log.insert(ignore_permissions=True)
			
			frappe.db.commit()

		elif action == "Stop":
			if row.status != "In Progress":
				# Cho phép dừng nếu trạng thái hiển thị sai, nhưng logic không tính giờ
				pass

			updates = {}
			duration = 0
			
			# Update Duration
			if row.last_start_time:
				start_time = frappe.utils.get_datetime(row.last_start_time)
				duration = (now - start_time).total_seconds()
				current_duration = flt(row.total_duration)
				updates["total_duration"] = current_duration + duration

			# Reset start time
			updates["last_start_time"] = None

			# Update Qty
			qty_to_add = cint(session_qty)
			if qty_to_add > 0:
				current_cut = cint(row.cut_qty)
				updates["cut_qty"] = current_cut + qty_to_add

			# Check completion
			new_cut_qty = cint(row.cut_qty) + qty_to_add
			if new_cut_qty >= row.qty:
				updates["status"] = "Completed"
			else:
				updates["status"] = "Pending"

			frappe.db.set_value("Cutting Pattern", row.name, updates)
			
			# Update the latest Running log for this pattern
			running_log = frappe.db.get_value(
				"Cutting Production Log",
				filters={
					"cutting_order": self.name,
					"pattern_idx": row.idx,
					"status": "Running"
				},
				fieldname="name",
				order_by="creation desc"
			)
			
			if running_log:
				log_updates = {
					"end_time": now,
					"duration_seconds": duration,
					"qty_cut": qty_to_add,
					"status": "Done"
				}
				if machine_no:
					log_updates["machine_no"] = machine_no
				if laser_speed:
					log_updates["laser_speed"] = cint(laser_speed)
				if issue_note:
					log_updates["issue_note"] = issue_note
					
				frappe.db.set_value("Cutting Production Log", running_log, log_updates)
			
			frappe.db.commit()

			# Update Parent Progress
			self.update_overall_progress_db_based()


	@frappe.whitelist()
	def get_pattern_statuses(self):
		return frappe.db.get_all(
			"Cutting Pattern",
			filters={"parent": self.name, "parenttype": "Cutting Order"},
			fields=["name", "status"],
		)

	def update_overall_progress_db_based(self):
		# Re-fetch doc to have latest Child values from DB
		new_doc = frappe.get_doc(self.doctype, self.name)
		new_doc.update_overall_progress()
		new_doc.save(ignore_permissions=True)

	def update_overall_progress(self):
		# 1. Reset produced_qty
		produced_map = defaultdict(int)

		total_required_cuts = 0
		total_made_cuts = 0
		total_duration = 0

		# 2. Iterate patterns and read from Pattern Segment child table
		for row in self.optimization_result:
			total_duration += flt(row.total_duration)
			if row.cut_qty > 0:
				# Get segments from Pattern Segment child table
				segments = frappe.db.get_all(
					"Pattern Segment",
					filters={"parent": row.name, "parenttype": "Cutting Pattern"},
					fields=["length_mm", "quantity"]
				)
				for seg in segments:
					length = flt(seg.length_mm)
					count = cint(seg.quantity)
					if length > 0 and count > 0:
						produced_map[length] += count * row.cut_qty

		# 3. Update Order Items (FIFO Distribution)
		# We use a copy to track remaining available cuts as we distribute them
		remaining_produced = produced_map.copy()

		for item in self.items:
			# Use flt for consistent key matching with pattern-parsed float lengths
			key = flt(item.length_mm)
			available = remaining_produced.get(key, 0)
			required = item.qty
			
			# Assign min(required, available) to this specific item row
			allocated = min(required, available)
			item.produced_qty = allocated
			
			# Calculate progress percentage
			if item.qty > 0:
				item.progress_percent = (item.produced_qty / item.qty) * 100.0
			else:
				item.progress_percent = 0
			
			# Decrement available count for next items of same length
			if key in remaining_produced:
				remaining_produced[key] = max(0, available - allocated)

			total_required_cuts += item.qty
			total_made_cuts += item.produced_qty

		# 4. Calculate %
		if total_required_cuts > 0:
			self.completion_percent = (total_made_cuts / total_required_cuts) * 100.0
		else:
			self.completion_percent = 0

		if self.completion_percent >= 100:
			self.status = "Completed"
		elif self.completion_percent > 0:
			self.status = "Planned"

		self.total_duration = total_duration


# Wrapper Methods
@frappe.whitelist()
def update_pattern_progress_wrapper(order_name, row_idx, action, session_qty=0, machine_no=None, laser_speed=None, issue_note=None):
	doc = frappe.get_doc("Cutting Order", order_name)
	doc.update_pattern_progress(row_idx, action, session_qty, machine_no, laser_speed, issue_note)


@frappe.whitelist()
def get_pattern_statuses_wrapper(order_name):
	return frappe.db.get_all(
		"Cutting Pattern",
		filters={"parent": order_name, "parenttype": "Cutting Order"},
		fields=["name", "idx", "status"],
		order_by="idx asc",
	)


@frappe.whitelist()
def update_cut_qty_wrapper(order_name, row_idx, new_qty):
	"""
	Update cut_qty for a pattern row. Only allowed for Admin and Kế hoạch sản xuất roles.
	"""
	# Check permissions
	allowed_roles = ["System Manager", "Administrator", "Production Manager", "Kế hoạch sản xuất"]
	user_roles = frappe.get_roles(frappe.session.user)
	
	has_permission = any(role in user_roles for role in allowed_roles)
	if not has_permission:
		frappe.throw("Bạn không có quyền sửa số lượng. Vui lòng liên hệ quản lý.")
	
	row_idx = cint(row_idx)
	new_qty = cint(new_qty)
	
	if new_qty < 0:
		frappe.throw("Số lượng không được âm.")
	
	# Get the pattern row
	patterns = frappe.db.get_all(
		"Cutting Pattern",
		filters={"parent": order_name, "parenttype": "Cutting Order"},
		fields=["name", "idx", "cut_qty"],
		order_by="idx asc",
	)
	
	target_row = None
	for p in patterns:
		if p.idx == row_idx:
			target_row = p
			break
	
	if not target_row:
		frappe.throw(f"Không tìm thấy row {row_idx}")
	
	old_qty = target_row.cut_qty or 0
	
	# Log the change
	frappe.log_error(
		message=f"User {frappe.session.user} changed cut_qty from {old_qty} to {new_qty} for pattern row {row_idx} in {order_name}",
		title="Cutting Qty Edit"
	)
	
	# Update
	frappe.db.set_value("Cutting Pattern", target_row.name, "cut_qty", new_qty)
	frappe.db.commit()
	
	# Recalculate order progress
	doc = frappe.get_doc("Cutting Order", order_name)
	doc.update_overall_progress_db_based()
	
	return {"success": True, "old_qty": old_qty, "new_qty": new_qty}


@frappe.whitelist()
def get_pattern_segments(pattern_name):
	"""Get segments for a Cutting Pattern (child table row)
	
	Since Pattern Segment is a child table (istable=1), 
	it has no permissions. This API fetches segments for display.
	"""
	if not pattern_name:
		return []
	
	segments = frappe.db.sql("""
		SELECT 
			piece_name, segment_name, steel_profile, length_mm, 
			quantity, punch_holes, rivet_holes, drill_holes, bending, note,
			source_spec, source_item
		FROM `tabPattern Segment`
		WHERE parent = %s AND parenttype = 'Cutting Pattern'
		ORDER BY idx ASC
	""", pattern_name, as_dict=True)
	
	return segments
