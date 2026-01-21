"""
Script to clean BOM-I3-001 by removing references to deleted items
"""
import frappe

def execute():
    try:
        bom = frappe.get_doc("BOM", "BOM-I3-001")
        
        # Items to remove (deleted items)
        items_to_remove = ["PHOI-I3.1", "PHOI-I3.2", "MANH-I3.1", "MANH-I3.2"]
        
        # Filter out invalid items
        valid_items = []
        removed_count = 0
        
        for item in bom.items:
            if item.item_code in items_to_remove:
                print(f"Removing {item.item_code} from BOM")
                removed_count += 1
            elif not frappe.db.exists("Item", item.item_code):
                print(f"Removing non-existent item {item.item_code} from BOM")
                removed_count += 1
            else:
                valid_items.append(item)
        
        if removed_count > 0:
            bom.items = []
            for item in valid_items:
                bom.append("items", {
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "uom": item.uom,
                })
            
            bom.save()
            frappe.db.commit()
            print(f"Removed {removed_count} invalid items from BOM-I3-001")
        else:
            print("No invalid items found in BOM-I3-001")
        
        return "Done"
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return str(e)
