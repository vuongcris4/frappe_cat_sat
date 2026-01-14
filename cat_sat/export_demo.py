# apps/cat_sat/cat_sat/export_demo.py
import json
import os

import frappe
from frappe.utils import get_path


def execute():
	"""
	Export toàn bộ dữ liệu demo của Cat Sat ra file JSON
	"""
	data = {}
	print("🚀 Bắt đầu xuất dữ liệu demo...")

	# 1. Master Data
	print("... Xuất Master Data")
	data["UOM"] = get_docs_safe("UOM")
	data["Item Group"] = get_docs_safe("Item Group")
	data["Item Attribute"] = get_docs_safe("Item Attribute")

	# 2. Items
	print("... Xuất Items (Raw Material + Products)")
	items = frappe.get_all(
		"Item",
		filters=[
			["Item", "disabled", "=", 0],
			["Item", "is_cutting_steel", "in", [0, 1]],
		],
		pluck="name",
	)
	data["Item"] = get_docs("Item", items)

	# 3. Cat Sat – CHỈ export Parent DocType
	parent_doctypes = [
		"Cutting Specification",
		"Cutting Requirement",
		"Cutting Plan",
		"Cutting Production Log",
		"Cutting Optimization Result",
	]

	for dt in parent_doctypes:
		print(f"... Xuất {dt}")
		data[dt] = get_docs_safe(dt)

	# 4. Ghi file (FIX: đảm bảo thư mục tồn tại)
	base_path = get_path("cat_sat")
	os.makedirs(base_path, exist_ok=True)

	file_path = os.path.join(base_path, "demo_data_dump.json")
	with open(file_path, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False, default=str)

	print(f"✅ Export thành công: {file_path}")


def get_docs_safe(doctype):
	"""
	Lấy toàn bộ document của 1 doctype (chỉ Parent, bỏ Child Table)
	"""
	meta = frappe.get_meta(doctype)
	if meta.istable:
		return []

	names = frappe.get_all(doctype, pluck="name")
	return get_docs(doctype, names)


def get_docs(doctype, names):
	"""
	Get docs an toàn, bỏ qua record lỗi / orphan
	"""
	docs = []

	for name in names:
		try:
			doc = frappe.get_doc(doctype, name)
			docs.append(doc.as_dict())
		except Exception:
			frappe.log_error(
				f"Skip export {doctype} {name}",
				"Cat Sat Export Demo",
			)

	return docs
