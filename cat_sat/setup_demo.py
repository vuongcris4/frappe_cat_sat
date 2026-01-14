# apps/cat_sat/cat_sat/setup_demo.py
import frappe
from frappe.utils import add_days, nowdate


def execute():
	frappe.db.begin()
	try:
		# 1. Tạo dữ liệu nền (UOM, Item Group, Attributes)
		create_essential_uoms()
		create_item_groups()
		setup_attributes()  # <--- Đã sửa logic để fix lỗi Attribute

		# 2. Tạo Item Thành phẩm
		create_finished_products()

		# 3. Tạo Sắt nguyên liệu
		create_raw_materials()

		# 4. Tạo BOM cắt & Kế hoạch
		spec_names = create_cutting_specifications()
		req_names = generate_requirements(spec_names)
		create_cutting_plan(req_names)

		frappe.db.commit()
		print("✅ Đã tạo dữ liệu mẫu thành công!")
	except Exception as e:
		frappe.db.rollback()
		print(f"❌ Lỗi khi tạo dữ liệu: {e!s}")
		frappe.log_error("Lỗi khởi tạo Demo Data Cat Sat")


def create_essential_uoms():
	"""Tạo các đơn vị tính cần thiết: Cái, Cây"""
	uoms = ["Cái", "Cây"]

	for uom_name in uoms:
		if not frappe.db.exists("UOM", uom_name):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom_name, "must_be_whole_number": 1}).insert(
				ignore_permissions=True
			)
			print(f"   -> Đã tạo UOM: {uom_name}")


def create_item_groups():
	"""Đảm bảo Item Group tồn tại"""
	# Tạo nhóm gốc trước
	if not frappe.db.exists("Item Group", "Raw Material"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Raw Material",
				"parent_item_group": "All Item Groups",
				"is_group": 1,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Item Group", "Products"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Products",
				"parent_item_group": "All Item Groups",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Item Group", "Thép ống"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Thép ống",
				"parent_item_group": "Raw Material",
				"is_group": 1,
			}
		).insert(ignore_permissions=True)

	sub_groups = ["Vuông", "Hộp", "Tròn", "V", "U"]
	for gr in sub_groups:
		if not frappe.db.exists("Item Group", gr):
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": gr,
					"parent_item_group": "Thép ống",
					"is_group": 0,
				}
			).insert(ignore_permissions=True)


def setup_attributes():
	"""
	Cấu hình Item Attribute.
	FIX: Chuyển Length sang dạng Non-Numeric (List) để tránh lỗi validate range phức tạp.
	"""
	# 1. Cấu hình Length
	attr_name = "Length"
	if not frappe.db.exists("Item Attribute", attr_name):
		frappe.get_doc(
			{
				"doctype": "Item Attribute",
				"attribute_name": attr_name,
				"numeric_values": 0,  # Tắt chế độ số
			}
		).insert(ignore_permissions=True)

	# Đảm bảo giá trị 6000 tồn tại trong danh sách cho phép
	doc = frappe.get_doc("Item Attribute", attr_name)
	doc.numeric_values = 0  # Force tắt numeric để tránh lỗi

	# Kiểm tra xem giá trị 6000 đã có chưa
	has_6000 = any(row.attribute_value == "6000" for row in doc.item_attribute_values)

	if not has_6000:
		doc.append("item_attribute_values", {"attribute_value": "6000", "abbr": "6m"})
		doc.save(ignore_permissions=True)

	# 2. Cấu hình các thuộc tính khác (Shape, Dimension, Thickness)
	attrs = ["Shape", "Dimension", "Thickness"]
	for attr in attrs:
		if not frappe.db.exists("Item Attribute", attr):
			frappe.get_doc({"doctype": "Item Attribute", "attribute_name": attr, "numeric_values": 0}).insert(
				ignore_permissions=True
			)

	print("   -> Đã cấu hình Attributes (Length=6000, Shape, ...)")


def create_finished_products():
	"""Tạo các Item thành phẩm (Bàn, Ghế)"""
	products = [
		{
			"item_code": "BAN-AN-01",
			"item_name": "Bàn Ăn Gia Đình (1m6)",
			"item_group": "Products",
			"stock_uom": "Cái",
			"is_stock_item": 1,
			"is_cutting_steel": 0,
		},
		{
			"item_code": "GHE-TUA-01",
			"item_name": "Ghế Tựa Lưng Thép",
			"item_group": "Products",
			"stock_uom": "Cái",
			"is_stock_item": 1,
			"is_cutting_steel": 0,
		},
	]

	for prod in products:
		if not frappe.db.exists("Item", prod["item_code"]):
			item = frappe.new_doc("Item")
			item.update(prod)
			item.insert(ignore_permissions=True)
			print(f"   -> Đã tạo Item: {prod['item_code']}")


def create_raw_materials():
	"""Tạo Item Sắt nguyên liệu (Template và Variants)"""

	template_code = "TUBE-STEEL"
	if not frappe.db.exists("Item", template_code):
		item = frappe.new_doc("Item")
		item.item_code = template_code
		item.item_name = "Thép ống"
		item.item_group = "Thép ống"
		item.stock_uom = "Cây"
		item.has_variants = 1
		item.is_stock_item = 1
		item.is_cutting_steel = 1
		item.bundle_sizes = "10,12,14"
		item.append("attributes", {"attribute": "Shape"})
		item.append("attributes", {"attribute": "Dimension"})
		item.append("attributes", {"attribute": "Thickness"})
		item.append("attributes", {"attribute": "Length"})
		item.insert(ignore_permissions=True)
		print(f"   -> Đã tạo Template: {template_code}")

	# 2. Tạo Variants
	# Lưu ý: Length phải là String "6000" để khớp với Attribute Value đã tạo
	variants = [
		{"Shape": "Vuông", "Dimension": "30x30", "Thickness": "5zem", "Length": "6000"},
		{"Shape": "Vuông", "Dimension": "40x80", "Thickness": "6zem", "Length": "6000"},
	]

	for attrs in variants:
		# Tên variant theo quy tắc đặt tên của ERPNext
		variant_code = (
			f"TUBE-STEEL-{attrs['Shape']}-{attrs['Dimension']}-{attrs['Thickness']}-{attrs['Length']}"
		)

		if not frappe.db.exists("Item", variant_code):
			variant = frappe.new_doc("Item")
			variant.item_code = variant_code
			variant.item_name = variant_code
			variant.variant_of = template_code
			variant.item_group = "Thép ống"
			variant.stock_uom = "Cây"
			variant.is_stock_item = 1
			variant.is_cutting_steel = 1

			for k, v in attrs.items():
				variant.append("attributes", {"attribute": k, "attribute_value": v})

			variant.insert(ignore_permissions=True)
			print(f"   -> Đã tạo Variant: {variant_code}")


def create_cutting_specifications():
	"""Tạo định mức cắt (BOM sắt) cho Bàn và Ghế"""
	raw_30x30 = "TUBE-STEEL-Vuông-30x30-5zem-6000"
	raw_40x80 = "TUBE-STEEL-Vuông-40x80-6zem-6000"

	specs = []

	# --- 1. Định mức cho Bàn Ăn ---
	if not frappe.db.exists("Cutting Specification", {"item_code": "BAN-AN-01"}):
		spec = frappe.new_doc("Cutting Specification")
		spec.item_code = "BAN-AN-01"

		# Mảnh 1: Chân bàn (cần 4 chân)
		piece1 = spec.append("pieces", {"piece_name": "Chân bàn", "piece_qty": 4})
		piece1.append(
			"details",
			{
				"steel_item": raw_40x80,
				"segment_name": "Thân chân",
				"length_mm": 720,
				"qty_segment_per_piece": 1,
			},
		)

		# Mảnh 2: Khung mặt bàn (cần 1 khung)
		piece2 = spec.append("pieces", {"piece_name": "Khung mặt bàn", "piece_qty": 1})
		piece2.append(
			"details",
			{
				"steel_item": raw_30x30,
				"segment_name": "Thanh dài",
				"length_mm": 1500,
				"qty_segment_per_piece": 2,
			},
		)
		piece2.append(
			"details",
			{
				"steel_item": raw_30x30,
				"segment_name": "Thanh ngắn",
				"length_mm": 700,
				"qty_segment_per_piece": 2,
			},
		)

		spec.insert(ignore_permissions=True)

		item = frappe.get_doc("Item", spec.item_code)
		item.cutting_specification = spec.name
		item.save(ignore_permissions=True)

		specs.append(spec.name)
		print(f"   -> Đã tạo Spec: {spec.name} cho Bàn Ăn")

	# --- 2. Định mức cho Ghế ---
	if not frappe.db.exists("Cutting Specification", {"item_code": "GHE-TUA-01"}):
		spec = frappe.new_doc("Cutting Specification")
		spec.item_code = "GHE-TUA-01"

		# Mảnh 1: Khung ghế tổng hợp
		piece = spec.append("pieces", {"piece_name": "Khung ghế", "piece_qty": 1})
		piece.append(
			"details",
			{
				"steel_item": raw_30x30,  # Dùng sắt 30x30 cho ghế
				"segment_name": "Chân trước",
				"length_mm": 450,
				"qty_segment_per_piece": 2,
			},
		)
		piece.append(
			"details",
			{
				"steel_item": raw_30x30,
				"segment_name": "Chân sau & Lưng",
				"length_mm": 900,
				"qty_segment_per_piece": 2,
			},
		)

		spec.insert(ignore_permissions=True)
		specs.append(spec.name)
		print(f"   -> Đã tạo Spec: {spec.name} cho Ghế")

	return specs


def generate_requirements(spec_names):
	"""Giả lập việc tạo Yêu cầu cắt (Cutting Requirement) từ đơn hàng"""
	req_ids = []

	# Tìm lại spec ID nếu không được truyền vào (trường hợp spec đã tồn tại từ trước)
	if not spec_names:
		ban_spec_name = frappe.db.get_value("Cutting Specification", {"item_code": "BAN-AN-01"})
		if ban_spec_name:
			spec_names.append(ban_spec_name)

		ghe_spec_name = frappe.db.get_value("Cutting Specification", {"item_code": "GHE-TUA-01"})
		if ghe_spec_name:
			spec_names.append(ghe_spec_name)

	for spec_name in spec_names:
		try:
			spec_doc = frappe.get_doc("Cutting Specification", spec_name)
			# Logic giả lập: Bàn làm 10 cái, Ghế làm 40 cái
			qty = 10 if spec_doc.item_code == "BAN-AN-01" else 40

			existing_req = frappe.db.exists(
				"Cutting Requirement", {"source_spec": spec_name, "status": "Generated"}
			)

			if existing_req:
				print(f"   -> Requirement cho {spec_doc.item_code} đã tồn tại: {existing_req}")
				req_ids.append(existing_req)
			else:
				cr_name = frappe.call(
					"cat_sat.cat_sat.api.generate_cutting_requirement", spec_name=spec_name, product_qty=qty
				)
				print(f"   -> Đã tạo Requirement cho {qty} {spec_doc.item_code}: {cr_name}")
				req_ids.append(cr_name)

		except Exception as e:
			print(f"   ! Lỗi tạo req cho {spec_name}: {e}")

	return req_ids


def create_cutting_plan(req_names):
	"""Gom các Requirement lại thành 1 Kế hoạch cắt (Cutting Plan)"""
	if not req_names:
		print("⚠️ Không có yêu cầu cắt nào để lập kế hoạch.")
		return

	plan = frappe.new_doc("Cutting Plan")
	plan.plan_date = nowdate()
	plan.status = "Draft"

	for req_name in req_names:
		plan.append("requirements", {"cutting_requirement": req_name})

	plan.insert(ignore_permissions=True)
	print(f"✅ Đã tạo Kế hoạch cắt: {plan.name}")

	# Thử chạy hàm lấy input cho Optimizer
	try:
		from cat_sat.cat_sat.services.cutting_plan_service import get_optimizer_input

		demand = get_optimizer_input(plan.name)
		print("\n--- KẾT QUẢ GỘP DEMAND (Input cho OR-Tools) ---")

		import json

		readable_demand = {str(k): v for k, v in demand.items()}
		print(json.dumps(readable_demand, indent=2, ensure_ascii=False))
	except Exception as e:
		print(f"⚠️ Không thể chạy thử get_optimizer_input: {e}")
