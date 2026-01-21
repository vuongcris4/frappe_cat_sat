"""
Script to add custom fields to Item DocType and import SKU mappings.
Run with: bench --site erp.dongnama.app execute cat_sat.scripts.setup_item_factory_code.run
"""

import frappe
import pandas as pd

def run():
    """Main function to setup factory_code and import mappings"""
    
    # Step 1: Create custom fields
    create_custom_fields()
    
    # Step 2: Import mappings from CSV
    import_sku_mappings()
    
    frappe.db.commit()
    print("✅ Setup completed successfully!")


def create_custom_fields():
    """Create custom fields on Item DocType"""
    
    fields = [
        {
            "dt": "Item",
            "fieldname": "factory_code",
            "label": "Mã nhà máy (Template)",
            "fieldtype": "Link",
            "options": "Item",
            "insert_after": "cutting_specification",
            "description": "Mã sản phẩm gốc để link với Cutting Specification"
        },
        {
            "dt": "Item",
            "fieldname": "rope_color",
            "label": "Màu dây",
            "fieldtype": "Data",
            "insert_after": "factory_code"
        },
        {
            "dt": "Item", 
            "fieldname": "cushion_color",
            "label": "Màu nệm",
            "fieldtype": "Data",
            "insert_after": "rope_color"
        }
    ]
    
    for field_def in fields:
        # Check if already exists
        if frappe.db.exists("Custom Field", {"dt": field_def["dt"], "fieldname": field_def["fieldname"]}):
            print(f"Field {field_def['fieldname']} already exists, skipping")
            continue
            
        # Create custom field
        cf = frappe.new_doc("Custom Field")
        cf.update(field_def)
        cf.insert(ignore_permissions=True)
        print(f"✅ Created custom field: {field_def['fieldname']}")
    
    frappe.clear_cache(doctype="Item")
    print("✅ Custom fields created successfully")


def import_sku_mappings():
    """Import SKU → factory_code + customer mappings from CSV"""
    
    import os
    bench_path = frappe.utils.get_bench_path()
    
    # Use Final_TachBo which has customer data
    csv_path = os.path.join(bench_path, "input_data", "Final_TachBo_ChiPhiDanMay.csv")
    
    if not os.path.exists(csv_path):
        csv_path = os.path.join(bench_path, "sites", frappe.local.site, "workspace", 
                                 "frappe-bench", "input_data", "Final_TachBo_ChiPhiDanMay.csv")
    
    print(f"Reading CSV from: {csv_path}")
    
    try:
        # Skip first row (BẢNG 1, BẢNG 2...), use second row as header
        df = pd.read_csv(csv_path, encoding='utf-8-sig', header=1)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # Clean up column names
    df.columns = [str(c).strip() for c in df.columns]
    print(f"Available columns: {list(df.columns)[:10]}")
    
    # Find relevant columns
    customer_col = "Tên khách hàng"
    sku_col = "Mã SKU"
    iea_col = "Mã IEA"
    color_col = "Màu dây"
    
    if sku_col not in df.columns or iea_col not in df.columns:
        print(f"❌ Required columns not found.")
        return
    
    # Process each row - aggregate unique SKUs
    sku_data = {}  # sku -> {factory_code, customer, rope_color}
    
    for _, row in df.iterrows():
        sku = str(row.get(sku_col, "")).strip()
        iea_code = str(row.get(iea_col, "")).strip()
        customer = str(row.get(customer_col, "")).strip() if customer_col in df.columns else ""
        rope_color = str(row.get(color_col, "")).strip() if color_col in df.columns else ""
        
        # Skip empty rows
        if not sku or not iea_code or sku == "nan" or iea_code == "nan":
            continue
        
        # Handle multiple SKUs separated by /
        for single_sku in sku.split("/"):
            single_sku = single_sku.strip()
            if not single_sku or single_sku == "nan":
                continue
            
            factory_code = normalize_iea_code(iea_code)
            
            if single_sku not in sku_data:
                sku_data[single_sku] = {
                    "factory_code": factory_code,
                    "customer": customer,
                    "rope_color": rope_color
                }
    
    # Update Items
    updated = 0
    not_found = 0
    
    for sku, data in sku_data.items():
        if not frappe.db.exists("Item", sku):
            not_found += 1
            continue
        
        # Find or match customer
        customer_name = None
        if data["customer"]:
            # Try to find existing customer
            customer_match = frappe.db.get_value("Customer", {"customer_name": ["like", f"%{data['customer'][:20]}%"]}, "name")
            if customer_match:
                customer_name = customer_match
        
        try:
            update_data = {
                "factory_code": data["factory_code"],
                "rope_color": data["rope_color"]
            }
            if customer_name:
                update_data["sku_customer"] = customer_name
            
            frappe.db.set_value("Item", sku, update_data, update_modified=False)
            updated += 1
        except Exception as e:
            print(f"❌ Error updating {sku}: {e}")
    
    frappe.db.commit()
    print(f"✅ Updated {updated} items, {not_found} SKUs not found in Items")


def normalize_iea_code(iea_code):
    """
    Normalize IEA code to match existing Item codes.
    
    Examples:
    - 'I3' → 'IEA-3'
    - 'I3 MỚI' → 'IEA-3'
    - 'J55.T4' → 'J55.T4'
    - 'J55.T4 NÂU' → 'J55.T4'
    - 'I9 I12.C2' → 'IEA-2' (combo, use first)
    """
    if not iea_code:
        return None
    
    # Remove extra descriptions like 'MỚI', 'NÂU', 'NỆM XANH' etc.
    parts = iea_code.split()
    base_code = parts[0].strip()
    
    # Handle J55 codes - keep as-is
    if base_code.startswith("J"):
        return base_code
    
    # Handle I{number} codes - convert to IEA-{number}
    if base_code.startswith("I") and len(base_code) > 1:
        num_part = base_code[1:]
        # Extract just the number
        num = ""
        for c in num_part:
            if c.isdigit():
                num += c
            else:
                break
        if num:
            return f"IEA-{num}"
    
    return base_code


if __name__ == "__main__":
    run()
