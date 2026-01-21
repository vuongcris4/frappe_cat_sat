#!/usr/bin/env python3
"""
Create Multi-Level BOM Structure from DinhMuc
Run: bench --site erp.dongnama.app execute cat_sat.scripts.create_btp_boms.create_all
"""
import pandas as pd
import frappe
import re
import os

# DinhMuc file path
DINHMUCAT_PATH = '/workspace/frappe-bench/input_data/DinhMuc/DinhMucVatTu16.1.2026.xlsx'
DINHMUCAT_GCN_PATH = '/workspace/frappe-bench/input_data/DinhMuc/DinhMucGCN.xlsx'

def normalize_profile(profile):
    """Normalize steel profile names"""
    profile = str(profile).upper().strip()
    
    patterns = [
        (r'V15', 'V15'), (r'V18', 'V18'), (r'V20', 'V20'), (r'V25', 'V25'),
        (r'V10', 'V10'), (r'V12', 'V12'), (r'V14', 'V14'),
        (r'H10.?20', 'H10-20'), (r'H13.?26', 'H13-26'), (r'H15.?35', 'H15-35'),
        (r'FI?4', 'Fi4'), (r'FI?6', 'Fi6'), (r'FI?8', 'Fi8'), 
        (r'FI?10', 'Fi10'), (r'FI?19', 'Fi19'),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, profile):
            return replacement
    
    return profile.replace(' ', '-')

def get_pieces_from_cutting_spec(product_code):
    """Get unique pieces from Cutting Specification"""
    if not frappe.db.exists("Cutting Specification", product_code):
        return []
    
    pieces = frappe.db.sql("""
        SELECT DISTINCT piece_code, piece_name 
        FROM `tabCutting Detail` 
        WHERE parent = %s AND piece_code IS NOT NULL
        ORDER BY piece_code
    """, product_code, as_dict=True)
    
    return pieces

def create_manh_han_item(piece_code, piece_name, product_code):
    """Create Mảnh Hàn Item"""
    item_code = f"MANH-{piece_code}"
    
    if frappe.db.exists("Item", item_code):
        return item_code
    
    try:
        doc = frappe.new_doc("Item")
        doc.item_code = item_code
        doc.item_name = f"Mảnh hàn {piece_name} - {product_code}"
        doc.item_group = "Mảnh Hàn"
        doc.stock_uom = "Cái"
        doc.is_stock_item = 1
        doc.insert(ignore_permissions=True)
        return item_code
    except Exception as e:
        print(f"  Error creating {item_code}: {e}")
        return None

def create_phoi_son_item(piece_code, piece_name, product_code):
    """Create Phôi Sơn Item"""
    item_code = f"PHOI-{piece_code}"
    
    if frappe.db.exists("Item", item_code):
        return item_code
    
    try:
        doc = frappe.new_doc("Item")
        doc.item_code = item_code
        doc.item_name = f"Phôi sơn {piece_name} - {product_code}"
        doc.item_group = "Phôi Sơn"
        doc.stock_uom = "Cái"
        doc.is_stock_item = 1
        doc.insert(ignore_permissions=True)
        return item_code
    except Exception as e:
        print(f"  Error creating {item_code}: {e}")
        return None

def create_manh_han_bom(manh_code, piece_code, product_code):
    """Create BOM for Mảnh Hàn from Cutting Details"""
    bom_name = f"BOM-{manh_code}-001"
    
    if frappe.db.exists("BOM", bom_name):
        return bom_name
    
    # Get cutting details for this piece
    details = frappe.db.sql("""
        SELECT steel_profile, length_mm, total_qty
        FROM `tabCutting Detail`
        WHERE parent = %s AND piece_code = %s
    """, (product_code, piece_code), as_dict=True)
    
    if not details:
        return None
    
    try:
        bom = frappe.new_doc("BOM")
        bom.item = manh_code
        bom.company = "Import Export Asia"
        bom.currency = "VND"
        bom.quantity = 1
        bom.is_active = 1
        bom.is_default = 1
        bom.with_operations = 0
        
        # Add steel segments
        for d in details:
            profile = normalize_profile(d.steel_profile)
            if frappe.db.exists("Item", profile):
                bom.append("items", {
                    "item_code": profile,
                    "qty": d.length_mm * d.total_qty  # Total mm
                })
        
        # Add welding materials
        if frappe.db.exists("Item", "DAY-HAN"):
            bom.append("items", {"item_code": "DAY-HAN", "qty": 0.01})
        if frappe.db.exists("Item", "KHI-CO2"):
            bom.append("items", {"item_code": "KHI-CO2", "qty": 0.02})
        if frappe.db.exists("Item", "TAN-RUT"):
            bom.append("items", {"item_code": "TAN-RUT", "qty": 2})
        
        bom.insert(ignore_permissions=True)
        
        # Link back to Cutting Details
        frappe.db.sql("""
            UPDATE `tabCutting Detail`
            SET bom_item = %s
            WHERE parent = %s AND piece_code = %s
        """, (manh_code, product_code, piece_code))
        
        return bom.name
    except Exception as e:
        print(f"  Error creating BOM for {manh_code}: {e}")
        return None

def create_phoi_son_bom(phoi_code, manh_code):
    """Create BOM for Phôi Sơn"""
    bom_name = f"BOM-{phoi_code}-001"
    
    if frappe.db.exists("BOM", bom_name):
        return bom_name
    
    if not frappe.db.exists("Item", manh_code):
        return None
    
    try:
        bom = frappe.new_doc("BOM")
        bom.item = phoi_code
        bom.company = "Import Export Asia"
        bom.currency = "VND"
        bom.quantity = 1
        bom.is_active = 1
        bom.is_default = 1
        bom.with_operations = 0
        
        # Add Mảnh hàn
        bom.append("items", {"item_code": manh_code, "qty": 1})
        
        # Add painting materials
        if frappe.db.exists("Item", "SON-TINH-DIEN"):
            bom.append("items", {"item_code": "SON-TINH-DIEN", "qty": 0.2})
        if frappe.db.exists("Item", "HOA-CHAT"):
            bom.append("items", {"item_code": "HOA-CHAT", "qty": 0.05})
        if frappe.db.exists("Item", "GAS"):
            bom.append("items", {"item_code": "GAS", "qty": 0.03})
        
        bom.insert(ignore_permissions=True)
        return bom.name
    except Exception as e:
        print(f"  Error creating BOM for {phoi_code}: {e}")
        return None

def process_product(product_code):
    """Process one product - create all BTP items and BOMs"""
    print(f"\n📦 Processing {product_code}...")
    
    pieces = get_pieces_from_cutting_spec(product_code)
    if not pieces:
        print(f"  ⚠ No pieces found in Cutting Spec")
        return 0
    
    created = 0
    
    for piece in pieces:
        piece_code = piece.piece_code
        piece_name = piece.piece_name or piece_code
        
        # Create Mảnh Hàn
        manh_code = create_manh_han_item(piece_code, piece_name, product_code)
        if manh_code:
            bom = create_manh_han_bom(manh_code, piece_code, product_code)
            if bom:
                print(f"  ✓ {manh_code} + BOM")
                created += 1
        
        # Create Phôi Sơn
        phoi_code = create_phoi_son_item(piece_code, piece_name, product_code)
        if phoi_code and manh_code:
            bom = create_phoi_son_bom(phoi_code, manh_code)
            if bom:
                print(f"  ✓ {phoi_code} + BOM")
                created += 1
    
    frappe.db.commit()
    return created

def create_all():
    """Create BTP structure for all products"""
    print("=== CREATING MULTI-LEVEL BOM STRUCTURE ===\n")
    
    # Get all Cutting Specifications
    specs = frappe.get_all("Cutting Specification", pluck="name")
    
    print(f"Found {len(specs)} Cutting Specifications")
    
    total_created = 0
    
    for spec in specs:
        created = process_product(spec)
        total_created += created
    
    print(f"\n=== COMPLETE ===")
    print(f"Total items/BOMs created: {total_created}")

if __name__ == "__main__":
    create_all()
