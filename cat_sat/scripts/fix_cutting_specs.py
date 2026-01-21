#!/usr/bin/env python3
"""
Fix Cutting Specification total_qty field
Run: bench --site erp.dongnama.app execute cat_sat.scripts.fix_cutting_specs.fix_total_qty
"""
import frappe

def fix_total_qty():
    """Update total_qty = qty_per_unit for all Cutting Details where total_qty is 0"""
    
    print("=== Fixing Cutting Specification total_qty ===")
    
    # Count before
    before = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabCutting Detail` 
        WHERE (total_qty IS NULL OR total_qty = 0) 
        AND qty_per_unit > 0
    """)[0][0]
    
    print(f"Records to fix: {before}")
    
    # Direct SQL update
    frappe.db.sql("""
        UPDATE `tabCutting Detail` 
        SET total_qty = qty_per_unit 
        WHERE (total_qty IS NULL OR total_qty = 0) 
        AND qty_per_unit > 0
    """)
    
    frappe.db.commit()
    
    # Count after
    after = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabCutting Detail` 
        WHERE (total_qty IS NULL OR total_qty = 0) 
        AND qty_per_unit > 0
    """)[0][0]
    
    print(f"Records remaining: {after}")
    print(f"Fixed: {before - after}")
    print("=== COMPLETE ===")

if __name__ == "__main__":
    fix_total_qty()
