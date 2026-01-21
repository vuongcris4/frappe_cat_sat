"""
Script to fix BOM-I3-001 quantities and create sub-BOMs
Based on GCN table from user
"""
import frappe

def execute():
    # === Step 1: Fix DAN quantities in BOM-I3-001 ===
    print("=== Fixing DAN quantities in BOM-I3-001 ===")
    
    # Correct quantities based on GCN table
    correct_qty = {
        "DAN-IEA 3.1.1": 2,  # Khung tựa - 1/ghế x 2 ghế = 2
        "DAN-IEA 3.1.2": 2,  # Tay trái - 1/ghế x 2 ghế = 2
        "DAN-IEA 3.1.3": 2,  # Tay phải - 1/ghế x 2 ghế = 2
        "DAN-IEA 3.1.4": 2,  # Mê ngồi - 1/ghế x 2 ghế = 2
        "DAN-IEA 3.2.1": 1,  # Mặt bàn - 1/bàn
        "DAN-IEA 3.2.2": 2,  # Hông bàn - 2/bàn
        "DAN-IEA 3.2.3": 2,  # Chân bàn - 2/bàn
    }
    
    bom = frappe.get_doc("BOM", "BOM-I3-001")
    for item in bom.items:
        if item.item_code in correct_qty:
            old_qty = item.qty
            item.qty = correct_qty[item.item_code]
            print(f"  {item.item_code}: {old_qty} → {item.qty}")
    
    bom.save()
    frappe.db.commit()
    print("BOM-I3-001 quantities fixed")
    
    # === Step 2: Create BOMs for DAN items ===
    print("\n=== Creating DAN BOMs ===")
    
    # DAN BOM structure (Cấp 2: PHOI + Dây đan + Đinh)
    dan_items = [
        {"dan": "DAN-IEA 3.1.1", "phoi": "PHOI-I3.1.1", "day": 0.66, "dinh": 95},
        {"dan": "DAN-IEA 3.1.2", "phoi": "PHOI-I3.1.2", "day": 0.70, "dinh": 117},
        {"dan": "DAN-IEA 3.1.3", "phoi": "PHOI-I3.1.3", "day": 0.70, "dinh": 117},
        {"dan": "DAN-IEA 3.1.4", "phoi": "PHOI-I3.1.4", "day": 0.72, "dinh": 223},
        {"dan": "DAN-IEA 3.2.1", "phoi": "PHOI-I3.2.1", "day": 0.46, "dinh": 137},
        {"dan": "DAN-IEA 3.2.2", "phoi": "PHOI-I3.2.2", "day": 0.42, "dinh": 126},
        {"dan": "DAN-IEA 3.2.3", "phoi": "PHOI-I3.2.3", "day": 0.48, "dinh": 122},
    ]
    
    for dan_data in dan_items:
        dan_code = dan_data["dan"]
        bom_name = f"BOM-{dan_code.replace(' ', '-')}-001"
        
        # Check if BOM already exists
        if frappe.db.exists("BOM", bom_name):
            print(f"  {bom_name} already exists, skipping")
            continue
        
        # Check if DAN item exists
        if not frappe.db.exists("Item", dan_code):
            print(f"  {dan_code} does not exist, skipping")
            continue
            
        # Check if PHOI item exists
        if not frappe.db.exists("Item", dan_data["phoi"]):
            print(f"  {dan_data['phoi']} does not exist, skipping")
            continue
        
        try:
            dan_bom = frappe.new_doc("BOM")
            dan_bom.item = dan_code
            dan_bom.quantity = 1
            dan_bom.is_active = 1
            dan_bom.is_default = 1
            dan_bom.company = "Import Export Asia"
            
            # Add PHOI
            dan_bom.append("items", {
                "item_code": dan_data["phoi"],
                "qty": 1,
            })
            
            # Add Dây đan (if exists)
            if frappe.db.exists("Item", "DAY-DAN"):
                dan_bom.append("items", {
                    "item_code": "DAY-DAN",
                    "qty": dan_data["day"],
                })
            
            # Add Đinh F10 (if exists)
            if frappe.db.exists("Item", "DINH-F10"):
                dan_bom.append("items", {
                    "item_code": "DINH-F10",
                    "qty": dan_data["dinh"],
                })
            
            dan_bom.insert()
            print(f"  Created {dan_bom.name}")
            
        except Exception as e:
            print(f"  Error creating BOM for {dan_code}: {e}")
    
    frappe.db.commit()
    
    print("\n=== Done ===")
    return "Done"
