import frappe


def get_items_for_profile(profile_code: str) -> list[dict]:
	"""
	Trả về danh sách cây sắt có thể dùng cho 1 Steel Profile
	đã sắp xếp theo priority
	"""
	profile = frappe.get_doc("Steel Profile", profile_code)

	items = []
	for row in profile.items:
		items.append(
			{
				"item": row.item,
				"length_mm": row.length_mm,
				"priority": row.priority or 99,
			}
		)

	return sorted(items, key=lambda x: x["priority"])
