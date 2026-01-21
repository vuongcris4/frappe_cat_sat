# -*- coding: utf-8 -*-
"""
Script to update Cutting Specification after BOM is created.

Run with:
    bench --site erp.dongnama.app execute cat_sat.migrations.update_cs_piece_names
"""
import frappe

def execute():
    """Update CS-00008 to link to Item and update piece names"""
    
    # Mapping: old piece_name -> new item_code
    piece_mapping = {
        "Khung trụ": "J55.MANH.KHUNG-TRU",
        "Khung trụa": "J55.MANH.KHUNG-TRU",  # typo fix
        "Tay trái": "J55.MANH.TAY-TRAI",
        "Tay phải": "J55.MANH.TAY-PHAI",
        "Mề ngoài": "J55.MANH.ME-NGOAI",
        "Hông trước": "J55.MANH.HONG-TRUOC",
    }
    
    # Update CS-00008 linked_item
    if frappe.db.exists("Cutting Specification", "CS-00008"):
        frappe.db.set_value("Cutting Specification", "CS-00008", "linked_item", "J55.C")
        print("✅ Updated CS-00008 linked_item = J55.C")
    
    # Update piece_name in Cutting Detail
    for old_name, new_name in piece_mapping.items():
        count = frappe.db.sql("""
            UPDATE `tabCutting Detail` 
            SET piece_name = %s 
            WHERE parent = 'CS-00008' AND piece_name = %s
        """, (new_name, old_name))
        print(f"  Updated '{old_name}' -> '{new_name}'")
    
    frappe.db.commit()
    print("✅ Migration completed!")


def submit_bom():
    """Submit the BOM"""
    bom = frappe.get_doc("BOM", "BOM-J55.C-001")
    bom.submit()
    print(f"✅ Submitted BOM {bom.name}")
