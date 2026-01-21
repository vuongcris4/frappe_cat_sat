"""
Import vidaXL Sales Orders from parsed JSON data.

Usage:
    bench --site erp.dongnama.app execute cat_sat.scripts.import_vidaxl_orders.run
"""

import frappe
import json
from frappe.utils import getdate


def run():
    """Main entry point for importing vidaXL orders."""
    
    # Load parsed data - use Docker container path
    json_path = "/workspace/frappe-bench/input_data/Sales order/sales_orders_full.json"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        sales_orders = json.load(f)
    
    print(f"Loading {len(sales_orders)} Sales Orders...")
    
    # Load SKU mapping
    sku_path = "/workspace/frappe-bench/input_data/Sales order/sku_mapping.json"
    with open(sku_path, 'r', encoding='utf-8') as f:
        sku_mapping = json.load(f)
    
    # Step 1: Create Items if they don't exist
    created_items = create_items_if_needed(sales_orders, sku_mapping)
    print(f"Created {len(created_items)} new Items")
    
    # Step 2: Create Sales Orders
    created_orders = create_sales_orders(sales_orders)
    print(f"Created {len(created_orders)} Sales Orders")
    
    frappe.db.commit()
    print("Import completed successfully!")
    
    return {
        'items_created': len(created_items),
        'orders_created': len(created_orders)
    }


def create_items_if_needed(sales_orders, sku_mapping):
    """Create Item records for each unique customer SKU."""
    
    # Collect unique SKUs from all orders
    unique_skus = {}
    for so in sales_orders:
        for item in so['items']:
            sku = item['customer_sku']
            if sku not in unique_skus:
                unique_skus[sku] = {
                    'shipping_mark': item.get('shipping_mark', ''),
                    'color': item.get('color', ''),
                    'art_no': item.get('art_no', ''),
                    'ctn_size': item.get('ctn_size', ''),
                    'factory_code': item.get('factory_code', ''),
                    'unit_price': item.get('unit_price', 0)
                }
    
    created = []
    
    for sku, info in unique_skus.items():
        # Check if item exists
        if frappe.db.exists("Item", sku):
            continue
        
        # Build item name from shipping mark and color
        item_name = info['shipping_mark'] if info['shipping_mark'] else f"vidaXL-{sku}"
        description = f"{info['color']}\n{info['art_no']}\nCTN: {info['ctn_size']}"
        if info['factory_code']:
            description += f"\nFactory Code: {info['factory_code']}"
        
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": sku,
            "item_name": item_name[:140],  # ERPNext limit
            "item_group": "Products",
            "stock_uom": "SET",
            "description": description,
            "is_sales_item": 1,
            "is_stock_item": 1,
            "include_item_in_manufacturing": 1,
            "custom_factory_code": info['factory_code'] if info['factory_code'] else None,
        })
        
        try:
            item.insert(ignore_permissions=True)
            created.append(sku)
            print(f"  Created Item: {sku} - {item_name[:40]}")
        except Exception as e:
            print(f"  Error creating Item {sku}: {e}")
    
    return created


def create_sales_orders(sales_orders):
    """Create Sales Order documents from parsed data."""
    
    created = []
    customer = "VIDAXL"
    
    for so_data in sales_orders:
        invoice_no = so_data['invoice_no']
        
        # Check if Sales Order already exists with this PI number
        existing = frappe.db.exists("Sales Order", {"po_no": invoice_no})
        if existing:
            print(f"  Skipping {invoice_no} - already exists")
            continue
        
        # Parse date
        try:
            date_str = so_data.get('invoice_date', '')
            if date_str:
                parts = date_str.strip().split('-')
                if len(parts) == 3:
                    year, month, day = parts
                    transaction_date = getdate(f"{year}-{month.zfill(2)}-{day.zfill(2)}")
                else:
                    transaction_date = frappe.utils.today()
            else:
                transaction_date = frappe.utils.today()
        except:
            transaction_date = frappe.utils.today()
        
        # Build items list
        items = []
        for item_data in so_data['items']:
            sku = item_data['customer_sku']
            
            # Make sure item exists
            if not frappe.db.exists("Item", sku):
                continue
            
            items.append({
                "item_code": sku,
                "qty": item_data['qty'],
                "rate": item_data['unit_price'],
                "delivery_date": transaction_date,
                "description": f"{item_data.get('color', '')}\n{item_data.get('art_no', '')}",
            })
        
        if not items:
            print(f"  Skipping {invoice_no} - no valid items")
            continue
        
        # Create Sales Order with all required fields
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "naming_series": "SAL-ORD-.YYYY.-",
            "company": "Import Export Asia",
            "customer": customer,
            "transaction_date": transaction_date,
            "delivery_date": transaction_date,
            "po_no": invoice_no,  # Store PI number as PO reference
            "po_date": transaction_date,
            "order_type": "Sales",
            "currency": "USD",
            "conversion_rate": 25000,
            "selling_price_list": "Standard Selling",
            "price_list_currency": "USD",
            "plc_conversion_rate": 1,
            "items": items,
        })
        
        try:
            so.insert(ignore_permissions=True)
            created.append(so.name)
            print(f"  Created Sales Order: {so.name} ({invoice_no})")
        except Exception as e:
            print(f"  Error creating SO {invoice_no}: {e}")
    
    return created


if __name__ == "__main__":
    run()
