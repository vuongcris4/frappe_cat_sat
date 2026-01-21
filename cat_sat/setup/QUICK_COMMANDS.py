# Quick Database Inspection Commands

# === IMPORT ===
from cat_sat.setup.db_inspector import *

# === BASIC COMMANDS ===

# 1. Tổng quan database
db()

# 2. Quick stats (số lượng records)
stats()

# 3. Chi tiết hơn
inspect_database(detailed=True)

# === VIEW ITEMS ===

# Tất cả items
items()

# Items theo group cụ thể
items("Ghế - JSE 55")
items("Thép Ống")
items("Sản phẩm IEA")

# === VIEW CUTTING SPECS ===

# Chi tiết 1 spec
spec("J55")
spec("J73")

# === EXAMPLES ===

# Xem tất cả Product Codes
import frappe
specs = frappe.get_all("Cutting Specification", fields=["name", "spec_name"])
for s in specs:
    print(f"{s.name}: {s.spec_name}")

# Xem items theo customer (nếu có custom field)
items_iea = frappe.get_all("Item", filters={"customer": "IEA"}, fields=["name", "item_name"])
print(f"IEA Products: {len(items_iea)}")

# Xem loại sắt nào đang được dùng
profiles = frappe.get_all("Steel Profile", fields=["profile_code"])
print("Steel Profiles:", [p.profile_code for p in profiles])
