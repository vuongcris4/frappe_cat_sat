"""
Script to link DAN BOMs to BOM-I3-001 and create PHOI BOMs
"""
import frappe

def execute():
    # === Step 1: Update BOM-I3-001 to link DAN BOMs ===
    print("=== Linking DAN BOMs to BOM-I3-001 ===")
    
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
    
    # === Step 2: Create PHOI BOMs ===
    print("\n=== Creating PHOI BOMs ===")
    
    # Get steel profile totals from Cutting Specification I3
    cutting_spec = frappe.get_doc("Cutting Specification", "I3")
    
    # Group steel by piece_code
    piece_steel = {}
    for detail in cutting_spec.details:
        piece_code = detail.piece_code
        if piece_code not in piece_steel:
            piece_steel[piece_code] = {}
        
        profile = detail.steel_profile
        length_mm = detail.length_mm * detail.qty_per_unit  # Total length per unit
        
        if profile not in piece_steel[piece_code]:
            piece_steel[piece_code][profile] = 0
        piece_steel[piece_code][profile] += length_mm
    
    print(f"  Found {len(piece_steel)} pieces in Cutting Spec")
    
    # Create PHOI BOMs
    phoi_mapping = {
        "I3.1.1": "PHOI-I3.1.1",
        "I3.1.2": "PHOI-I3.1.2", 
        "I3.1.3": "PHOI-I3.1.3",
        "I3.1.4": "PHOI-I3.1.4",
        "I3.2.1": "PHOI-I3.2.1",
        "I3.2.2": "PHOI-I3.2.2",
        "I3.2.3": "PHOI-I3.2.3",
    }
    
    for piece_code, phoi_code in phoi_mapping.items():
        if piece_code not in piece_steel:
            print(f"  {piece_code} not found in Cutting Spec")
            continue
            
        if not frappe.db.exists("Item", phoi_code):
            print(f"  {phoi_code} item does not exist")
            continue
        
        bom_name = f"BOM-{phoi_code}-001"
        if frappe.db.exists("BOM", bom_name):
            print(f"  {bom_name} already exists")
            continue
        
        try:
            phoi_bom = frappe.new_doc("BOM")
            phoi_bom.item = phoi_code
            phoi_bom.quantity = 1
            phoi_bom.is_active = 1
            phoi_bom.is_default = 1
            phoi_bom.company = "Import Export Asia"
            
            # Add steel items (by profile, total mm)
            for profile, total_mm in piece_steel[piece_code].items():
                if frappe.db.exists("Item", profile):
                    phoi_bom.append("items", {
                        "item_code": profile,
                        "qty": total_mm,
                        "uom": "mm",
                    })
            
            phoi_bom.insert()
            print(f"  Created {phoi_bom.name}")
            
        except Exception as e:
            print(f"  Error creating BOM for {phoi_code}: {e}")
    
    frappe.db.commit()
    
    # === Step 3: Link PHOI BOMs to DAN BOMs ===
    print("\n=== Linking PHOI BOMs to DAN BOMs ===")
    
    dan_phoi_links = [
        ("BOM-DAN-IEA 3.1.1-002", "PHOI-I3.1.1", "BOM-PHOI-I3.1.1-001"),
        ("BOM-DAN-IEA 3.1.2-002", "PHOI-I3.1.2", "BOM-PHOI-I3.1.2-001"),
        ("BOM-DAN-IEA 3.1.3-002", "PHOI-I3.1.3", "BOM-PHOI-I3.1.3-001"),
        ("BOM-DAN-IEA 3.1.4-002", "PHOI-I3.1.4", "BOM-PHOI-I3.1.4-001"),
        ("BOM-DAN-IEA 3.2.1-002", "PHOI-I3.2.1", "BOM-PHOI-I3.2.1-001"),
        ("BOM-DAN-IEA 3.2.2-002", "PHOI-I3.2.2", "BOM-PHOI-I3.2.2-001"),
        ("BOM-DAN-IEA 3.2.3-002", "PHOI-I3.2.3", "BOM-PHOI-I3.2.3-001"),
    ]
    
    for dan_bom_name, phoi_item, phoi_bom_name in dan_phoi_links:
        if not frappe.db.exists("BOM", dan_bom_name):
            continue
        if not frappe.db.exists("BOM", phoi_bom_name):
            continue
            
        dan_bom = frappe.get_doc("BOM", dan_bom_name)
        for item in dan_bom.items:
            if item.item_code == phoi_item:
                item.bom_no = phoi_bom_name
                print(f"  {dan_bom_name}: {phoi_item} → {phoi_bom_name}")
        dan_bom.save()
    
    frappe.db.commit()
    
    print("\n=== Done ===")
    return "Done"
