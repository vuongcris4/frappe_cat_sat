import frappe


def get_optimizer_input(plan_name: str) -> dict:
	plan = frappe.get_doc("Cutting Plan", plan_name)
	demand = {}

	for row in plan.requirements:
		# plan.requirements now contains the data directly
		key = (row.steel_profile, row.length_mm)
		demand[key] = demand.get(key, 0) + row.qty

	return demand


@frappe.whitelist()
def generate_requirements(plan):
	# Clear existing requirements
	plan.set("requirements", [])
	
	# Mapping key: (steel_profile, length_mm, segment_name)
	aggregated_requirements = {}

	for row in plan.items:
		spec_name = frappe.db.get_value("Item", row.item_code, "cutting_specification")

		if not spec_name:
			frappe.throw(f"Thành phẩm {row.item_code} chưa được gán Bảng cắt sắt")
			
		spec = frappe.get_doc("Cutting Specification", spec_name)
		
		# --- Logic Replicating flatten_bom but preserving segment_name ---
		
		# 1. Piece map: { clean_name: qty }
		piece_qty_map = {
			(p.piece_name.strip() if p.piece_name else ""): (p.piece_qty or 0) for p in spec.pieces
		}
		
		product_qty = int(row.product_qty)

		for d in spec.details:
			piece_name = d.piece_name
			if not piece_name:
				continue

			clean_piece_name = piece_name.strip()
			piece_qty = piece_qty_map.get(clean_piece_name, 0)

			# Total segments for this entry
			total_segment = (d.qty_segment_per_piece or 0) * piece_qty * product_qty

			if total_segment > 0:
				# Use segment_name from detail if available, else fallback to piece_name
				# Actually field 'segment_name' exists in Cutting Detail.
				actual_segment_name = d.segment_name or clean_piece_name
				
				# Aggregation Key: (steel_profile, length_mm, actual_segment_name)
				agg_key = (d.steel_profile, d.length_mm, actual_segment_name)
				aggregated_requirements[agg_key] = aggregated_requirements.get(agg_key, 0) + total_segment

	# Add to child table
	for (steel_profile, length_mm, segment_name), qty in aggregated_requirements.items():
		plan.append("requirements", {
			"steel_profile": steel_profile,
			"length_mm": length_mm,
			"qty": qty,
			"segment_name": segment_name
		})

@frappe.whitelist()
def generate_requirements_from_plan(plan_name: str):
    # Wrapper for API compatibility if needed, though we are removing the button
    plan = frappe.get_doc("Cutting Plan", plan_name)
    generate_requirements(plan)
    plan.save()


@frappe.whitelist()
def create_cutting_orders(plan_name: str):
	plan = frappe.get_doc("Cutting Plan", plan_name)
	
	if not plan.requirements:
		frappe.throw("Vui lòng tạo danh sách yêu cầu cắt trước (Bấm Save)")

	# Group by steel_profile
	grouped_reqs = {}
	for row in plan.requirements:
		if row.steel_profile not in grouped_reqs:
			grouped_reqs[row.steel_profile] = []
		grouped_reqs[row.steel_profile].append(row)

	created_orders = []

	for steel_profile, rows in grouped_reqs.items():
		# Check if exists
		exists = frappe.db.exists("Cutting Order", {
			"cutting_plan": plan.name,
			"steel_profile": steel_profile
		})
		
		if exists:
			continue

		# Create new Order
		co = frappe.new_doc("Cutting Order")
		co.cutting_plan = plan.name
		co.steel_profile = steel_profile
		co.stock_length = 6000 # Default, should ideally come from Item attribute
		
		for r in rows:
			co.append("items", {
				"length_mm": r.length_mm,
				"qty": r.qty,
				"segment_name": r.segment_name
			})
			
		co.insert()
		created_orders.append(co.name)
		
	if created_orders:
		frappe.msgprint(f"Đã tạo {len(created_orders)} Lệnh cắt: {', '.join(created_orders)}")
	else:
		frappe.msgprint("Không có Lệnh cắt nào mới được tạo (có thể đã tồn tại).")

	return created_orders
