#!/usr/bin/env python3
"""
Update BOM quantities from DinhMucVatTu
Run: bench --site erp.dongnama.app execute cat_sat.scripts.update_bom_qty.update_all
"""
import pandas as pd
import frappe
import re

DINHMUCAT_PATH = '/workspace/frappe-bench/input_data/DinhMuc/DinhMucVatTu16.1.2026.xlsx'

# Sheet to product mapping
SHEET_MAP = {
    'IEA3=IEA 7=IEA 24': ['I3', 'I7', 'I24'],
    'IEA 1=IEA 27=IEA31': ['I1', 'I27', 'I31'],
    'IEA 2=IEA 32=IEA 36': ['I2', 'I32', 'I36'],
    'IEA 4=JSE 46': ['I4', 'J46'],
    'IEA 5 XÁM =IEA 5 NÂU': ['I5'],
    'IEA 6=JSE 47': ['I6', 'J47'],
    'IEA 8': ['I8'],
    'IEA 9': ['I9'],
    'IEA 22 THÙNG SỌT': ['I22'],
    'IEA 25': ['I25'],
    'IEA 28=IEA 33': ['I28', 'I33'],
    'IEA 29=IEA 34': ['I29', 'I34'],
    'IEA 30=IEA 35': ['I30', 'I35'],
    'J15': ['J15'],
    'J48': ['J48'],
    'J49': ['J49'],
    'JSE 66': ['J66'],
    'JSE 67': ['J67'],
}

def parse_materials(df):
    """Parse materials from DinhMuc sheet"""
    materials = {}
    
    for idx, row in df.iterrows():
        if pd.notna(row.iloc[0]) and str(row.iloc[0]).strip().isdigit():
            ten_nvl = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
            try:
                dm = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0
            except:
                dm = 0
            
            if ten_nvl and 'TỔNG' not in ten_nvl.upper() and dm > 0:
                # Normalize material name
                nvl_code = normalize_material(ten_nvl)
                if nvl_code:
                    materials[nvl_code] = dm
    
    return materials

def normalize_material(name):
    """Normalize material name to item code"""
    name = name.upper().strip()
    
    # Steel profiles
    if 'V15' in name:
        return 'V15'
    elif 'V10' in name:
        return 'V10'
    elif 'V18' in name:
        return 'V18'
    elif 'H10-20' in name or 'H10*20' in name:
        return 'H10-20'
    elif 'FI 4' in name or 'FI4' in name:
        return 'Fi4'
    elif 'FI 6' in name or 'FI6' in name:
        return 'Fi6'
    elif 'F19' in name or 'FI19' in name:
        return 'Fi19'
    elif 'DÂY NÂU' in name:
        return 'DAY-NAU-08'
    elif 'DÂY XÁM' in name:
        return 'DAY-XAM'
    elif 'SƠN TĨNH ĐIỆN' in name:
        return 'SON-TINH-DIEN'
    elif 'HÓA CHẤT' in name:
        return 'HOA-CHAT'
    elif 'KHÍ CO2' in name:
        return 'KHI-CO2'
    elif 'DÂY HÀN' in name:
        return 'DAY-HAN'
    elif 'TÁN RÚT' in name:
        return 'TAN-RUT'
    
    return None

def update_bom_items(bom_name, materials_qty):
    """Update BOM item quantities"""
    try:
        bom = frappe.get_doc("BOM", bom_name)
        updated = 0
        
        for item in bom.items:
            # Check if this item is in our materials map
            if item.item_code in materials_qty:
                new_qty = materials_qty[item.item_code]
                
                # Convert cm to mm if needed (DinhMuc uses cm)
                if item.uom == 'mm':
                    new_qty = new_qty * 10
                
                if item.qty != new_qty:
                    item.qty = new_qty
                    updated += 1
        
        if updated > 0:
            bom.save(ignore_permissions=True)
            return updated
        
        return 0
        
    except Exception as e:
        print(f"  Error: {e}")
        return 0

def update_all():
    """Update all BOMs from DinhMuc"""
    print("=== UPDATING BOM QUANTITIES FROM DINHIMUC ===\n")
    
    xl = pd.ExcelFile(DINHMUCAT_PATH)
    
    total_updated = 0
    
    for sheet, products in SHEET_MAP.items():
        if sheet not in xl.sheet_names:
            continue
        
        print(f"\n📄 Processing sheet: {sheet}")
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        materials = parse_materials(df)
        
        print(f"   Materials found: {len(materials)}")
        
        for product in products:
            bom_name = f"BOM-{product}-001"
            if frappe.db.exists("BOM", bom_name):
                updated = update_bom_items(bom_name, materials)
                if updated > 0:
                    print(f"   ✓ {bom_name}: {updated} items updated")
                    total_updated += updated
    
    frappe.db.commit()
    
    print(f"\n=== COMPLETE ===")
    print(f"Total items updated: {total_updated}")

if __name__ == "__main__":
    update_all()
