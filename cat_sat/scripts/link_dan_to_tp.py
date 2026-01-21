#!/usr/bin/env python3
"""
Link Mảnh Đan items to finished product BOMs
Run: bench --site erp.dongnama.app execute cat_sat.scripts.link_dan_to_tp.link_all
"""
import frappe
import re

# Product to DAN item prefix mapping
PRODUCT_DAN_MAP = {
    'I1': ['IEA 1-27-31', 'DAN-IEA 1'],
    'I2': ['IEA 2-32-36', 'DAN-IEA 2'],
    'I3': ['IEA 3-7-24', 'IEA 3', 'DAN-IEA 3'],
    'I4': ['JSE 46', 'DAN-JSE 46'],
    'I5': ['IEA 5', 'DAN-IEA 5'],
    'I6': ['IEA 6-JSE 47', 'IEA 6-47', 'DAN-IEA 6'],
    'I8': ['IEA 8', 'DAN-IEA 8'],
    'I9': ['IEA 9', 'DAN-IEA 9'],
    'J15': ['JSE 15', 'DAN-JSE 15'],
    'J48': ['JSE 48', 'DAN-JSE 48'],
    'J49': ['JSE 49', 'DAN-JSE 49'],
    'J55.C': ['JSE 55', 'DAN-JSE 55'],
    'J66': ['JSE 66', 'DAN-JSE 66'],
    'J67': ['JSE 67', 'DAN-JSE 67'],
}

def find_dan_items(prefixes):
    """Find DAN items matching prefixes"""
    items = []
    for prefix in prefixes:
        result = frappe.db.sql("""
            SELECT name, item_name 
            FROM tabItem 
            WHERE item_group = 'Mảnh Đan' 
            AND name LIKE %s
        """, f"DAN-{prefix}%", as_dict=True)
        items.extend(result)
    return items

def update_bom_with_dan(bom_name, dan_items):
    """Add DAN items to BOM"""
    if not dan_items:
        return 0
    
    try:
        bom = frappe.get_doc("BOM", bom_name)
        
        # Check existing items
        existing = [i.item_code for i in bom.items]
        
        added = 0
        for dan in dan_items:
            if dan.name not in existing:
                bom.append("items", {
                    "item_code": dan.name,
                    "qty": 1
                })
                added += 1
        
        if added > 0:
            bom.save(ignore_permissions=True)
        
        return added
        
    except Exception as e:
        print(f"  Error: {e}")
        return 0

def link_all():
    """Link DAN items to all finished product BOMs"""
    print("=== LINKING MẢNH ĐAN TO FINISHED PRODUCT BOMS ===\n")
    
    total_added = 0
    
    for product, prefixes in PRODUCT_DAN_MAP.items():
        bom_name = f"BOM-{product}-001"
        
        if not frappe.db.exists("BOM", bom_name):
            print(f"⚠ {bom_name} not found")
            continue
        
        dan_items = find_dan_items(prefixes)
        
        if dan_items:
            added = update_bom_with_dan(bom_name, dan_items)
            if added > 0:
                print(f"✓ {bom_name}: +{added} DAN items")
                total_added += added
            else:
                print(f"⏭ {bom_name}: already has DAN items")
        else:
            print(f"⚠ {bom_name}: No DAN items found")
    
    frappe.db.commit()
    
    print(f"\n=== COMPLETE ===")
    print(f"Total DAN items added: {total_added}")

if __name__ == "__main__":
    link_all()
