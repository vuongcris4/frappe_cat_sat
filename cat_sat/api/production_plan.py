# Copyright (c) 2026, IEA and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict


@frappe.whitelist()
def generate_cutting_plans(production_plan):
    """
    Generate ONE Cutting Plan from a Production Plan.
    Consolidates all items into a single plan for optimal steel cutting.
    
    Args:
        production_plan: Name of the Production Plan document
        
    Returns:
        List with the created Cutting Plan name
    """
    pp = frappe.get_doc("Production Plan", production_plan)
    
    if pp.docstatus != 1:
        frappe.throw(_("Production Plan must be submitted before generating Cutting Plans"))
    
    # Check if Cutting Plan already exists for this Production Plan
    existing = frappe.db.exists("Cutting Plan", {"work_order": production_plan})
    if existing:
        frappe.throw(_("Cutting Plan already exists for this Production Plan: {0}").format(existing))
    
    # Get items from Production Plan
    items_field = "po_items" if pp.get("po_items") else "mr_items"
    items = pp.get(items_field) or []
    
    if not items:
        frappe.throw(_("No items found in Production Plan"))
    
    # Collect all items with their cutting specs
    valid_items = []
    earliest_delivery = None
    
    for item in items:
        item_code = item.item_code
        qty = item.planned_qty
        sales_order = item.get("sales_order")
        
        # Get cutting specification for item
        spec = get_cutting_spec_for_item(item_code)
        
        if spec:
            valid_items.append({
                "item_code": item_code,
                "qty": qty,
                "sales_order": sales_order
            })
            
            # Track earliest delivery date
            if sales_order:
                delivery_date = frappe.db.get_value(
                    "Sales Order", sales_order, "delivery_date"
                )
                if delivery_date:
                    if not earliest_delivery or delivery_date < earliest_delivery:
                        earliest_delivery = delivery_date
        else:
            frappe.msgprint(
                _("No cutting specification found for item {0}. Skipping.").format(item_code),
                alert=True
            )
    
    if not valid_items:
        frappe.throw(_("No items with cutting specifications found"))
    
    # Create ONE Cutting Plan with all items
    try:
        cp = frappe.new_doc("Cutting Plan")
        cp.work_order = production_plan
        cp.plan_name = pp.name  # Simple name, no suffix
        cp.plan_date = pp.posting_date
        
        if earliest_delivery:
            cp.target_date = earliest_delivery
        
        # Add ALL items to the same cutting plan
        for item in valid_items:
            cp.append("items", {
                "item_code": item["item_code"],
                "product_qty": item["qty"]
            })
        
        cp.insert(ignore_permissions=True)
        
        # Generate requirements - this will aggregate across all items
        if hasattr(cp, 'generate_requirements'):
            try:
                cp.generate_requirements()
                cp.save()
            except Exception as e:
                frappe.log_error(
                    message=str(e),
                    title=f"Error generating requirements for {cp.name}"
                )
        
        frappe.msgprint(
            _("Created Cutting Plan: {0} with {1} products").format(cp.name, len(valid_items)),
            indicator="green"
        )
        
        return [cp.name]
        
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"Error creating Cutting Plan for {production_plan}"
        )
        frappe.throw(_("Error creating Cutting Plan: {0}").format(str(e)))


def get_cutting_spec_for_item(item_code):
    """
    Get cutting specification for an item.
    Uses 2-layer architecture: checks direct spec, then factory_code.
    
    Args:
        item_code: The Item code
        
    Returns:
        Cutting Specification name or None
    """
    item_data = frappe.db.get_value(
        "Item", 
        item_code,
        ["cutting_specification", "factory_code"],
        as_dict=True
    )
    
    if not item_data:
        return None
    
    # 1. Check direct cutting_specification on item
    if item_data.get("cutting_specification"):
        return item_data["cutting_specification"]
    
    # 2. Lookup via factory_code
    factory_code = item_data.get("factory_code")
    if factory_code:
        factory_spec = frappe.db.get_value(
            "Item", 
            factory_code, 
            "cutting_specification"
        )
        if factory_spec:
            return factory_spec
    
    # 3. Try to match item code to cutting spec directly
    # E.g., IEA-3 exists and I3 is a Cutting Spec
    if item_code.startswith("IEA-"):
        spec_name = "I" + item_code[4:]  # IEA-3 -> I3
        if frappe.db.exists("Cutting Specification", spec_name):
            return spec_name
    
    # 4. Lookup by item_template field on Cutting Specification
    # This is the standard way - Cutting Specification has item_template linking to Item
    spec = frappe.db.get_value(
        "Cutting Specification",
        {"item_template": item_code},
        "name"
    )
    if spec:
        return spec
    
    return None


@frappe.whitelist()
def get_cutting_plans_for_production_plan(production_plan):
    """
    Get list of Cutting Plans linked to a Production Plan.
    
    Args:
        production_plan: Name of Production Plan
        
    Returns:
        List of Cutting Plan documents
    """
    plans = frappe.get_all(
        "Cutting Plan",
        filters={"work_order": production_plan},
        fields=["name", "plan_name", "status", "plan_date", "target_date"]
    )
    return plans
