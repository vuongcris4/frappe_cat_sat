"""
Script to update I3 Cutting Specification with descriptive segment names
Format: {steel_profile} ({machining details})
"""
import frappe

def execute():
    doc = frappe.get_doc("Cutting Specification", "I3")
    
    for detail in doc.details:
        # Build descriptive name from steel_profile and machining details
        parts = [detail.steel_profile]
        
        machining = []
        if detail.bend_type and detail.bend_type != "Không":
            bend_map = {
                "Uốn 1 đầu": "uốn 1 đầu",
                "Uốn 2 đầu": "uốn 2 đầu", 
                "Uốn cong": "uốn"
            }
            machining.append(bend_map.get(detail.bend_type, "uốn"))
        
        if detail.punch_hole_qty and detail.punch_hole_qty > 0:
            machining.append(f"{detail.punch_hole_qty} dập")
        
        if detail.rivet_hole_qty and detail.rivet_hole_qty > 0:
            machining.append(f"{detail.rivet_hole_qty} tán")
            
        if detail.drill_hole_qty and detail.drill_hole_qty > 0:
            machining.append(f"{detail.drill_hole_qty} khoan")
        
        if machining:
            desc = f"{detail.steel_profile} ({', '.join(machining)})"
        else:
            desc = detail.steel_profile
        
        old_name = detail.segment_name
        detail.segment_name = desc
        print(f"  {old_name} → {desc}")
    
    doc.save()
    frappe.db.commit()
    print(f"\nUpdated {len(doc.details)} segments")
    return "Done"
