import frappe
from frappe.model.naming import make_autoname

def execute():
    plans = frappe.get_all("Cutting Plan", fields=["name", "creation", "plan_name"], order_by="creation asc")
    
    print(f"Found {len(plans)} plans to process.")
    
    # Group by MM-YYYY to manage counters
    counters = {}

    for plan in plans:
        # Skip if already matches format (heuristic)
        if plan.name.startswith("KH-"):
            print(f"Skipping {plan.name} (already formatted)")
            continue

        # Ensure plan_name is set (required field)
        if not plan.plan_name:
            frappe.db.set_value("Cutting Plan", plan.name, "plan_name", f"Batch {plan.name[:5]}")
            print(f"Updated plan_name for {plan.name}")

        # Generate new name
        # Format: KH-.MM.-.YYYY.-.#####
        # We need to construct it manually to respect creation date
        created_date = plan.creation
        month = created_date.strftime("%m")
        year = created_date.strftime("%Y")
        key = f"{month}-{year}"
        
        if key not in counters:
            # Check DB for existing max count for this pattern?
            # For simplicity, since these are likely the ONLY records, we start from 1 
            # or try to find gaps. But safest is to start from 1 and increment til free.
            counters[key] = 0
        
        while True:
            counters[key] += 1
            new_name = f"KH-{month}-{year}-{counters[key]:05d}"
            if not frappe.db.exists("Cutting Plan", new_name):
                break
        
        try:
            old_name = plan.name
            frappe.rename_doc("Cutting Plan", old_name, new_name, force=True)
            print(f"Renamed {old_name} -> {new_name}")
            
            # Commit after each rename to be safe or all at once? 
            # execute() script usually auto commits at end, but rename_doc does its own commits often.
            frappe.db.commit()
            
        except Exception as e:
            print(f"Failed to rename {plan.name}: {str(e)}")

