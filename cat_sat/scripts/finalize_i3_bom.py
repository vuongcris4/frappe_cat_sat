"""
Script to add missing CO2 and SON-TD to BOM-I3-001
"""
import frappe

def execute():
    try:
        bom = frappe.get_doc("BOM", "BOM-I3-001")
        
        # Check which items to add
        existing_items = [item.item_code for item in bom.items]
        
        items_to_add = [
            {"item_code": "CO2", "qty": 1.383, "uom": "Kg"},
            {"item_code": "SON-TD", "qty": 0.242, "uom": "Kg"},
        ]
        
        for item in items_to_add:
            if item["item_code"] not in existing_items:
                if frappe.db.exists("Item", item["item_code"]):
                    bom.append("items", {
                        "item_code": item["item_code"],
                        "qty": item["qty"],
                        "uom": item.get("uom", "Cái"),
                    })
                    print(f"Added {item['item_code']} to BOM-I3-001")
        
        bom.save()
        frappe.db.commit()
        print("BOM-I3-001 updated successfully")
        
        # Delete old PHOI and MANH items
        old_items = ["PHOI-I3.1", "PHOI-I3.2", "MANH-I3.1", "MANH-I3.2"]
        for item_code in old_items:
            if frappe.db.exists("Item", item_code):
                try:
                    frappe.delete_doc("Item", item_code, force=True)
                    print(f"Deleted {item_code}")
                except Exception as e:
                    print(f"Could not delete {item_code}: {e}")
        
        frappe.db.commit()
        return "Done"
        
    except Exception as e:
        print(f"Error: {e}")
        return str(e)
