import frappe


def execute():
	if frappe.db.exists("Item", "TUBE-STEEL"):
		template = frappe.get_doc("Item", "TUBE-STEEL")

		variants = [
			{"Shape": "Vuông", "Dimension": "30x30", "Thickness": "5zem", "Length": 6000},
			{"Shape": "Vuông", "Dimension": "40x80", "Thickness": "6zem", "Length": 6000},
		]

		for attrs in variants:
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"TUBE-STEEL-{attrs['Shape']}-{attrs['Dimension']}-{attrs['Thickness']}-{attrs['Length']}",
					"variant_of": template.name,
					"attributes": [{"attribute": k, "attribute_value": v} for k, v in attrs.items()],
					"item_group": "Thép ống",
					"stock_uom": "Cây",
					"is_stock_item": 1,
					"maintain_stock": 1,
					"is_cutting_steel": 1,
					"bundle_sizes": "10,12,14",
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()
