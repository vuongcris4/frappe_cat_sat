"""
Import Goplus PI files.
Structure: CONTRACT NO. | ITEM NO. | CTNS | BAR CODE

Usage:
    bench --site erp.dongnama.app execute cat_sat.scripts.import_goplus_orders.run
"""

import frappe
import pandas as pd
import glob
import os
import re


def run():
    """Import Goplus PI orders."""
    
    base = "/workspace/frappe-bench/input_data/DonHang/DonHangGoplus"
    
    # Get PI files only
    pi_files = [f for f in glob.glob(f"{base}/*.xlsx") if os.path.basename(f).startswith("PI")]
    print(f"Found {len(pi_files)} Goplus PI files")
    
    results = {"orders_created": 0, "items_created": 0}
    
    for fpath in pi_files:
        fname = os.path.basename(fpath)
        
        # Extract PO number from filename
        po_match = re.search(r'(SCBW\d+HE-\d|CA\d+HE-\d|FDK\d+BD-\d)', fname)
        po_no = po_match.group(1) if po_match else fname.split('.xlsx')[0][:30]
        
        # Check if already exists
        if frappe.db.exists("Sales Order", {"po_no": po_no}):
            print(f"Skipping {po_no} - already exists")
            continue
        
        print(f"Processing: {fname}")
        df = pd.read_excel(fpath, sheet_name=0, header=None)
        
        # Parse items (skip header row 0)
        items = []
        for idx, row in df.iterrows():
            if idx == 0:  # Skip header
                continue
            
            item_no = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
            ctns = int(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
            
            if not item_no or ctns <= 0:
                continue
            
            # Create Item if not exists
            if not frappe.db.exists("Item", item_no):
                item = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": item_no,
                    "item_name": item_no,
                    "item_group": "Products",
                    "stock_uom": "Nos",
                    "is_sales_item": 1,
                    "is_stock_item": 1,
                    "include_item_in_manufacturing": 1,
                })
                item.insert(ignore_permissions=True)
                results["items_created"] += 1
            
            items.append({
                "item_code": item_no,
                "qty": ctns,
                "rate": 0,  # No price in file
                "delivery_date": frappe.utils.today(),
            })
        
        if not items:
            print(f"  No valid items found")
            continue
        
        # Create Sales Order
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "naming_series": "SAL-ORD-.YYYY.-",
            "company": "Import Export Asia",
            "customer": "GOPLUS",
            "transaction_date": frappe.utils.today(),
            "delivery_date": frappe.utils.today(),
            "po_no": po_no,
            "order_type": "Sales",
            "currency": "USD",
            "conversion_rate": 25000,
            "selling_price_list": "Standard Selling",
            "price_list_currency": "USD",
            "plc_conversion_rate": 1,
            "items": items,
        })
        
        so.insert(ignore_permissions=True)
        results["orders_created"] += 1
        print(f"  Created: {so.name} ({po_no}) - {len(items)} items")
    
    frappe.db.commit()
    
    print(f"\nSUMMARY: {results['orders_created']} orders, {results['items_created']} items created")
    return results


if __name__ == "__main__":
    run()
