#!/usr/bin/env python3
"""
Update Finished Product BOMs to use PHOI items instead of raw materials
Run: bench --site erp.dongnama.app execute cat_sat.scripts.update_tp_boms.update_all
"""
import frappe

def get_phoi_items_for_product(product_code):
    """Get all PHOI items created for this product"""
    # Handle multiple naming patterns:
    # I3 -> PHOI-I3.1, PHOI-I3.2
    # I11 -> PHOI-11.1.1, PHOI-11.1.2 (without I prefix)
    # I30 -> PHOI-30.1.1
    # IEA-3 -> PHOI-IEA3.1.1
    
    # Extract numeric part
    import re
    num_match = re.search(r'(\d+)', product_code)
    num = num_match.group(1) if num_match else product_code
    
    # Search multiple patterns
    phoi_items = frappe.db.sql("""
        SELECT name, item_name 
        FROM tabItem 
        WHERE item_group = 'Phôi Sơn' 
        AND (
            name LIKE %s 
            OR name LIKE %s 
            OR name LIKE %s 
            OR name LIKE %s
        )
    """, (
        f"PHOI-{product_code}.%",   # PHOI-I3.1
        f"PHOI-{product_code}%",    # PHOI-I3.1.1
        f"PHOI-{num}.%",            # PHOI-3.1 (numeric only)
        f"PHOI-IEA{num}.%"          # PHOI-IEA3.1.1
    ), as_dict=True)
    
    return phoi_items

def update_tp_bom(bom_name, phoi_items):
    """Update a finished product BOM to use PHOI items"""
    if not phoi_items:
        return False
    
    try:
        bom = frappe.get_doc("BOM", bom_name)
        
        # Clear existing items (raw materials)
        bom.items = []
        
        # Add PHOI items
        for phoi in phoi_items:
            bom.append("items", {
                "item_code": phoi.name,
                "qty": 1  # Typically 1 piece per finished product
            })
        
        bom.save(ignore_permissions=True)
        return True
        
    except Exception as e:
        print(f"  Error updating {bom_name}: {e}")
        return False

def update_all():
    """Update all finished product BOMs"""
    print("=== UPDATING FINISHED PRODUCT BOMS ===\n")
    
    # Get all BOMs for finished products (I1, I2, I3...)
    tp_boms = frappe.db.sql("""
        SELECT b.name, b.item
        FROM tabBOM b
        JOIN tabItem i ON b.item = i.name
        WHERE i.item_group = 'Sản phẩm IEA'
        AND b.is_default = 1
    """, as_dict=True)
    
    print(f"Found {len(tp_boms)} finished product BOMs")
    
    updated = 0
    skipped = 0
    
    for bom in tp_boms:
        product = bom.item
        phoi_items = get_phoi_items_for_product(product)
        
        if phoi_items:
            print(f"📦 {bom.name} ({product}): {len(phoi_items)} PHOI items")
            if update_tp_bom(bom.name, phoi_items):
                print(f"  ✓ Updated")
                updated += 1
            else:
                skipped += 1
        else:
            print(f"⚠ {bom.name} ({product}): No PHOI items found")
            skipped += 1
    
    frappe.db.commit()
    
    print(f"\n=== COMPLETE ===")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")

if __name__ == "__main__":
    update_all()
