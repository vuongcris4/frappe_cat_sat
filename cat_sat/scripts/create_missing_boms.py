#!/usr/bin/env python3
"""
Create BOMs for missing J55/J61 variants
Run: bench --site erp.dongnama.app execute cat_sat.scripts.create_missing_boms.create_all
"""
import frappe

MISSING_ITEMS = [
    'J61.S4', 'J61.S2', 'J61.C4', 'J61.C2',
    'J55.T8.C8', 'J55.T8.C4', 'J55.T6.C6', 'J55.T6.C3',
    'J55.T4.C4', 'J55.T4-DAY.DEN-MAT.KINH', 'J55.T4-GP-DAY.NAU-MAT.GO',
    'J55.T4-MY-DAY.DEN-MAT.KINH', 'J55.T4-DAY.NAU-MAT.GO', 'J55.T4',
    'J55.C-DAY.DEN-NEM.BE', 'J55.C-DAY.XBE-NEM.BE', 'J55.C-VX-DAY.NAU-NEM.DO',
    'J55.C-MY-DAY.XBE-NEM.BE', 'J55.C-DAY.NAU-NEM.DO',
    'J55.T4.C4-DAY.DEN-NEM.BE-MAT.KINH', 'J55.T6', 'GP-J55.T4.C4'
]

# Base BOMs to inherit from
BASE_BOM_MAP = {
    'J61': 'J61.C',  # J61 variants inherit from J61.C (ghế)
    'J55.T': 'J55.C',  # J55 table variants
    'J55.C': 'J55.C',  # J55 chair variants
}

def get_base_items(item_code):
    """Get base item to copy BOM from"""
    if 'J61.S' in item_code:  # Đôn
        return find_dan_items('JSE 61')
    elif 'J61.C' in item_code:  # Ghế
        return find_dan_items('JSE 61')
    elif 'J55.T' in item_code:  # Bàn
        return find_dan_items('JSE 55')
    elif 'J55.C' in item_code:  # Ghế
        return find_dan_items('JSE 55')
    return []

def find_dan_items(prefix):
    """Find DAN items with matching prefix"""
    items = frappe.db.sql("""
        SELECT name FROM tabItem 
        WHERE item_group = 'Mảnh Đan' 
        AND name LIKE %s
    """, f"DAN-{prefix}%", as_list=True)
    return [i[0] for i in items]

def create_bom(item_code):
    """Create BOM for item using DAN items"""
    bom_name = f"BOM-{item_code.replace('.', '-')}-001"
    
    if frappe.db.exists("BOM", bom_name):
        print(f"  ⏭ {bom_name} exists")
        return bom_name
    
    if not frappe.db.exists("Item", item_code):
        print(f"  ⚠ Item {item_code} not found")
        return None
    
    dan_items = get_base_items(item_code)
    
    if not dan_items:
        print(f"  ⚠ No DAN items for {item_code}")
        return None
    
    try:
        bom = frappe.new_doc("BOM")
        bom.item = item_code
        bom.company = "Import Export Asia"
        bom.currency = "VND"
        bom.quantity = 1
        bom.is_active = 1
        bom.is_default = 1
        bom.with_operations = 0
        
        # Add DAN items
        for dan in dan_items[:5]:  # Limit to first 5
            bom.append("items", {"item_code": dan, "qty": 1})
        
        bom.insert(ignore_permissions=True)
        return bom.name
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None

def create_all():
    """Create BOMs for all missing items"""
    print("=== CREATING MISSING BOMS ===\n")
    
    created = 0
    skipped = 0
    
    for item in MISSING_ITEMS:
        print(f"📦 {item}...")
        result = create_bom(item)
        if result and 'exists' not in str(result):
            print(f"  ✓ Created {result}")
            created += 1
        else:
            skipped += 1
    
    frappe.db.commit()
    
    print(f"\n=== COMPLETE ===")
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")

if __name__ == "__main__":
    create_all()
