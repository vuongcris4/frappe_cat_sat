import re
import unicodedata

import frappe


# XOÁ DẤU
def slugify(text):
	text = unicodedata.normalize("NFD", text)
	text = "".join(c for c in text if unicodedata.category(c) != "Mn")
	text = text.lower()
	text = re.sub(r"[^a-z0-9\.]+", "-", text)
	return text.strip("-")


# Lấy abbr từ tabItem Attribute Value
def get_abbr(attribute_name, attribute_value):
	return (
		frappe.db.get_value(
			"Item Attribute Value",
			{
				"parent": attribute_name,
				"attribute_value": attribute_value,
			},
			"abbr",
		)
		or attribute_value
	)


def set_variant_name(doc, method):
	if not doc.variant_of:
		return

	attrs = {a.attribute: a.attribute_value for a in doc.attributes}

	# Lấy ABBREVIATION
	hinh_dang = get_abbr("Hình dạng", attrs.get("Hình dạng"))
	kich_thuoc = attrs.get("Kích thước sắt")  # thường là số → không cần abbr
	do_day = attrs.get("Độ dày")
	chieu_dai = attrs.get("Chiều dài")

	if not all([hinh_dang, kich_thuoc, do_day, chieu_dai]):
		return

	item_name = f"Sắt-{hinh_dang}{kich_thuoc}_{do_day}*{chieu_dai}"
	item_code = slugify(item_name)

	doc.item_name = item_name
	doc.item_code = item_code
