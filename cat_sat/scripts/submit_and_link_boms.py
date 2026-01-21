"""
Script to submit DAN BOMs and link to BOM-I3-001
"""
import frappe

def execute():
    # === Step 1: Submit DAN BOMs ===
    print("=== Submitting DAN BOMs ===")
    
    dan_boms = [
        "BOM-DAN-IEA 3.1.1-002",
        "BOM-DAN-IEA 3.1.2-002",
        "BOM-DAN-IEA 3.1.3-002",
        "BOM-DAN-IEA 3.1.4-002",
        "BOM-DAN-IEA 3.2.1-002",
        "BOM-DAN-IEA 3.2.2-002",
        "BOM-DAN-IEA 3.2.3-002",
    ]
    
    for bom_name in dan_boms:
        if frappe.db.exists("BOM", bom_name):
            bom = frappe.get_doc("BOM", bom_name)
            if bom.docstatus == 0:  # Draft
                try:
                    bom.submit()
                    print(f"  Submitted {bom_name}")
                except Exception as e:
                    print(f"  Error submitting {bom_name}: {e}")
            else:
                print(f"  {bom_name} already submitted")
    
    frappe.db.commit()
    
    # === Step 2: Link DAN BOMs to BOM-I3-001 ===
    print("\n=== Linking DAN BOMs to BOM-I3-001 ===")
    
    bom = frappe.get_doc("BOM", "BOM-I3-001")
    
    dan_bom_links = {
        "DAN-IEA 3.1.1": "BOM-DAN-IEA 3.1.1-002",
        "DAN-IEA 3.1.2": "BOM-DAN-IEA 3.1.2-002",
        "DAN-IEA 3.1.3": "BOM-DAN-IEA 3.1.3-002",
        "DAN-IEA 3.1.4": "BOM-DAN-IEA 3.1.4-002",
        "DAN-IEA 3.2.1": "BOM-DAN-IEA 3.2.1-002",
        "DAN-IEA 3.2.2": "BOM-DAN-IEA 3.2.2-002",
        "DAN-IEA 3.2.3": "BOM-DAN-IEA 3.2.3-002",
    }
    
    for item in bom.items:
        if item.item_code in dan_bom_links:
            bom_no = dan_bom_links[item.item_code]
            if frappe.db.exists("BOM", bom_no):
                item.bom_no = bom_no
                print(f"  {item.item_code} → {bom_no}")
    
    bom.save()
    frappe.db.commit()
    print("BOM-I3-001 linked to sub-BOMs")
    
    print("\n=== Done ===")
    return "Done"
