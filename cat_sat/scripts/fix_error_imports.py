"""
Fix import for 4 files that had fractional qty errors.
These files have different column structure - TOTAL QTY at col 10, RATE at col 14.

Usage:
    bench --site erp.dongnama.app execute cat_sat.scripts.fix_error_imports.run
"""

import frappe
import pandas as pd
import glob
import os
import re


def run():
    """Fix import for error files."""
    
    base = "/workspace/frappe-bench/input_data/DonHang/DonHangMeying"
    
    error_files = [
        "T5 IEA-FSD2025050700046.xlsx",
        "T5 IEA-FSD2025050700045.xlsx",
        "T10 15.10 IEA FSD2024101500003.xlsx",
        "FSD20210520-025 IEA.xlsx"
    ]
    
    files = glob.glob(f"{base}/*.xlsx")
    results = {"orders_created": 0, "items_created": 0}
    
    for ef in error_files:
        # Find matching file
        matched = [f for f in files if ef.split('.xlsx')[0] in os.path.basename(f)]
        if not matched:
            print(f"File not found: {ef}")
            continue
        
        fpath = matched[0]
        fname = os.path.basename(fpath)
        
        # Extract PO number
        po_match = re.search(r'(FSD\d+|IEA-FSD\d+)', fname)
        po_no = po_match.group(1) if po_match else fname.replace('.xlsx', '')
        
        # Check if already exists
        if frappe.db.exists("Sales Order", {"po_no": po_no}):
            print(f"Skipping {po_no} - already exists")
            continue
        
        print(f"Processing: {fname}")
        df = pd.read_excel(fpath, sheet_name=0, header=None)
        
        # Parse items with corrected column indices
        # Col 10: TOTAL QTY, Col 14: USD PRICE FOB
        items = []
        for idx, row in df.iterrows():
            if idx < 10:
                continue
                
            sku = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
            if not sku.startswith("V-"):
                continue
            
            # Use col 10 for qty, col 14 for rate
            qty = row.iloc[10] if len(row) > 10 and pd.notna(row.iloc[10]) else 0
            rate = row.iloc[14] if len(row) > 14 and pd.notna(row.iloc[14]) else 0
            factory_code = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
            description = str(row.iloc[5]) if len(row) > 5 and pd.notna(row.iloc[5]) else ""
            
            # Convert qty to integer
            try:
                qty = int(float(qty))
            except:
                qty = 0
            
            if qty <= 0:
                continue
            
            # Create Item if not exists
            if not frappe.db.exists("Item", sku):
                item = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": sku,
                    "item_name": sku[:140],
                    "item_group": "Products",
                    "stock_uom": "SET",
                    "description": f"{factory_code}\n{description[:200]}",
                    "is_sales_item": 1,
                    "is_stock_item": 1,
                    "include_item_in_manufacturing": 1,
                })
                item.insert(ignore_permissions=True)
                results["items_created"] += 1
            
            items.append({
                "item_code": sku,
                "qty": qty,
                "rate": rate,
                "delivery_date": frappe.utils.today(),
                "description": description[:140],
            })
        
        if not items:
            print(f"  No valid items found")
            continue
        
        # Create Sales Order
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "naming_series": "SAL-ORD-.YYYY.-",
            "company": "Import Export Asia",
            "customer": "MEYING",
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
        print(f"  Created: {so.name} ({po_no}) - {len(items)} items, ${so.grand_total:,.2f}")
    
    frappe.db.commit()
    
    print(f"\nSUMMARY: {results['orders_created']} orders, {results['items_created']} items created")
    return results


if __name__ == "__main__":
    run()
