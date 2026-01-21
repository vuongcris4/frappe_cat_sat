"""
Script to update Cutting Specification I3 with correct 7-piece structure
and update BOM-I3-001 with production supplies
"""
import frappe

def execute():
    # Update Cutting Specification I3 piece_code to match 7-piece structure
    # Mapping from segment name to correct piece_code
    piece_mapping = {
        # Ghế pieces (I3.1.x)
        "I3.1.1": "I3.1.1",  # Khung tựa
        "I3.1.2": "I3.1.2",  # Tay trái  
        "I3.1.3": "I3.1.3",  # Tay phải
        "I3.1.4": "I3.1.4",  # Mê ngồi
        # Bàn pieces (I3.2.x)
        "I3.2.1": "I3.2.1",  # Mặt bàn
        "I3.2.2": "I3.2.2",  # Hông bàn
        "I3.2.3": "I3.2.3",  # Chân bàn
    }
    
    piece_names = {
        "I3.1.1": "Khung tựa",
        "I3.1.2": "Tay trái",
        "I3.1.3": "Tay phải",
        "I3.1.4": "Mê ngồi",
        "I3.2.1": "Mặt bàn",
        "I3.2.2": "Hông bàn",
        "I3.2.3": "Chân bàn",
    }
    
    doc = frappe.get_doc("Cutting Specification", "I3")
    
    for detail in doc.details:
        # Extract piece_code from segment_name (e.g., I3.1.1.1 -> I3.1.1)
        parts = detail.segment_name.split(".")
        if len(parts) >= 3:
            new_piece_code = f"I3.{parts[1]}.{parts[2]}"
            if new_piece_code in piece_names:
                detail.piece_code = new_piece_code
                detail.piece_name = piece_names[new_piece_code]
                detail.bom_item = f"PHOI-{new_piece_code}"
    
    doc.save()
    frappe.db.commit()
    print(f"Updated {len(doc.details)} cutting details with correct piece codes")
    
    # Now update BOM-I3-001 to add production supplies
    try:
        bom = frappe.get_doc("BOM", "BOM-I3-001")
        
        # Production supplies to add (for the whole product)
        supplies = [
            {"item_code": "DAY-HAN", "qty": 6.506, "uom": "Kg"},
            {"item_code": "CO2", "qty": 1.383, "uom": "Kg"},
            {"item_code": "TAN-RUT", "qty": 30, "uom": "Cái"},
            {"item_code": "SON-TD", "qty": 0.242, "uom": "Kg"},
            {"item_code": "HOA-CHAT", "qty": 0.036, "uom": "Kg"},
            {"item_code": "GAS", "qty": 0.161, "uom": "Kg"},
        ]
        
        # Check which supplies already exist in BOM
        existing_items = [item.item_code for item in bom.items]
        
        for supply in supplies:
            if supply["item_code"] not in existing_items:
                # Check if item exists
                if frappe.db.exists("Item", supply["item_code"]):
                    bom.append("items", {
                        "item_code": supply["item_code"],
                        "qty": supply["qty"],
                        "uom": supply.get("uom", "Cái"),
                    })
                    print(f"Added {supply['item_code']} to BOM-I3-001")
                else:
                    print(f"Item {supply['item_code']} does not exist, skipping")
        
        bom.save()
        frappe.db.commit()
        print("Updated BOM-I3-001 with production supplies")
        
    except Exception as e:
        print(f"Error updating BOM: {e}")
    
    return "Done"

