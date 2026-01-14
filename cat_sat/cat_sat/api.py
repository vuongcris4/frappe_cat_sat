import frappe


@frappe.whitelist()
def generate_cutting_requirement(spec_name, product_qty=1):
	spec = frappe.get_doc("Cutting Specification", spec_name)

	bom = spec.flatten_bom(int(product_qty))

	cr = frappe.new_doc("Cutting Requirement")
	cr.source_spec = spec.name
	cr.status = "Generated"

	for (
		steel_profile,
		length_mm,
		bend_type,
		punch_hole_qty,
		rivet_hole_qty,
	), qty in bom.items():
		cr.append(
			"items",
			{
				"steel_profile": steel_profile,
				"length_mm": length_mm,
				"bend_type": bend_type,
				"punch_hole_qty": punch_hole_qty,
				"rivet_hole_qty": rivet_hole_qty,
				"total_qty": qty,
			},
		)

	cr.insert()
	return cr.name
