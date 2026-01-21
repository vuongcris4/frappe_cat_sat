"""
Import Sales Orders from DonHang directory:
- Goplus PI files (4 orders)
- Meying IEA-FSD files (102 orders)

Usage:
    bench --site erp.dongnama.app execute cat_sat.scripts.import_donhang_orders.run
"""

import frappe
import pandas as pd
import glob
import os
import re
from frappe.utils import getdate


def run():
    """Main entry point."""
    
    base = "/workspace/frappe-bench/input_data/DonHang"
    
    results = {
        "items_created": 0,
        "orders_created": 0,
        "errors": []
    }
    
    # Import Meying orders
    print("=" * 60)
    print("IMPORTING MEYING IEA-FSD ORDERS")
    print("=" * 60)
    
    meying_files = glob.glob(f"{base}/DonHangMeying/*FSD*.xlsx")
    print(f"Found {len(meying_files)} Meying FSD files")
    
    for fpath in meying_files:
        try:
            result = import_meying_order(fpath)
            if result.get("order_created"):
                results["orders_created"] += 1
            results["items_created"] += result.get("items_created", 0)
        except Exception as e:
            results["errors"].append(f"{os.path.basename(fpath)}: {str(e)}")
            print(f"  Error: {os.path.basename(fpath)}: {e}")
    
    frappe.db.commit()
    
    print("\n" + "=" * 60)
    print(f"SUMMARY")
    print("=" * 60)
    print(f"Orders created: {results['orders_created']}")
    print(f"Items created: {results['items_created']}")
    print(f"Errors: {len(results['errors'])}")
    
    return results


def import_meying_order(fpath):
    """Import a single Meying FSD order."""
    
    fname = os.path.basename(fpath)
    
    # Extract PO number
    po_match = re.search(r'(FSD\d+|IEA-FSD\d+)', fname)
    po_no = po_match.group(1) if po_match else fname.replace('.xlsx', '').replace('Copy of ', '')
    
    # Check if already exists
    if frappe.db.exists("Sales Order", {"po_no": po_no}):
        print(f"  Skipping {po_no} - already exists")
        return {"order_created": False, "items_created": 0}
    
    df = pd.read_excel(fpath, sheet_name=0, header=None)
    
    # Parse items (rows 10+ with valid SKU in column 1)
    items = []
    items_created = 0
    
    for idx, row in df.iterrows():
        if idx < 10:  # Skip header rows
            continue
            
        sku = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
        
        # Valid Meying SKU starts with V-
        if not sku.startswith("V-"):
            continue
            
        # Check if this is TOTAL row
        if "TOTAL" in str(row.iloc[4]) if pd.notna(row.iloc[4]) else "":
            break
            
        # Extract data
        qty = float(row.iloc[9]) if pd.notna(row.iloc[9]) else 0  # TOTAL QTY
        rate = float(row.iloc[13]) if pd.notna(row.iloc[13]) else 0  # USD PRICE FOB
        factory_code = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
        description = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ""
        
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
            items_created += 1
        
        items.append({
            "item_code": sku,
            "qty": qty,
            "rate": rate,
            "delivery_date": frappe.utils.today(),
            "description": description[:140],
        })
    
    if not items:
        print(f"  No items found in {po_no}")
        return {"order_created": False, "items_created": items_created}
    
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
    print(f"  Created: {so.name} ({po_no}) - {len(items)} items, ${so.grand_total:,.2f}")
    
    return {"order_created": True, "items_created": items_created}


if __name__ == "__main__":
    run()
