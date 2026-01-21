#!/usr/bin/env python3
"""
Create Mảnh Đan Items and BOMs from DinhMucGCN
Run: bench --site erp.dongnama.app execute cat_sat.scripts.create_dan_boms.create_all
"""
import pandas as pd
import frappe
import re

DINHMUCAT_GCN_PATH = '/workspace/frappe-bench/input_data/DinhMuc/DinhMucGCN.xlsx'

# Product mapping from sheet names
SHEET_PRODUCT_MAP = {
    'JSE 15': 'J15',
    'JSE 48': 'J48',
    'JSE 49': 'J49',
    'JSE 66': 'J66',
    'JSE 67': 'J67',
    'JSE 55 GOPLUS': 'J55.C',
    'JSE 46=IEA 4': 'I4',
    'IEA 1=IEA 27=IEA 31': 'I1',
    'IEA 2=IEA 32=IEA 36': 'I2',
    'IEA3=IEA 7=IEA 24': 'I3',
    'IEA 3 GOPLUS': 'I3',
    'IEA 5 MEIJING.GSS': 'I5',
    'IEA 6': 'I6',
    'IEA 8': 'I8',
    'MÃ IEA 9': 'I9',
}

def parse_gcn_sheet(df, sheet_name):
    """Parse GCN sheet to extract Mảnh đan data"""
    dan_items = []
    
    # Find header row
    for idx, row in df.iterrows():
        row_str = ' '.join([str(c) for c in row if pd.notna(c)])
        if 'Mã hàng' in row_str or 'STT' in row_str:
            header_row = idx
            break
    else:
        return []
    
    # Parse data rows
    for idx in range(header_row + 2, len(df)):
        row = df.iloc[idx]
        
        # Check if row has valid data
        if pd.isna(row.iloc[1]) or not str(row.iloc[1]).strip():
            continue
        
        ma_hang = str(row.iloc[1]).strip()
        ten_hang = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ma_hang
        
        # Skip total/summary rows
        if 'TỔNG' in ma_hang.upper() or 'tổng' in ma_hang.lower():
            continue
        
        # Get values
        try:
            dm_sat = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0
            dm_day = float(row.iloc[7]) if pd.notna(row.iloc[7]) else 0
            dm_dinh = float(row.iloc[8]) if pd.notna(row.iloc[8]) else 0
        except:
            dm_sat = dm_day = dm_dinh = 0
        
        if dm_sat > 0 or dm_day > 0:
            dan_items.append({
                'ma_hang': ma_hang,
                'ten_hang': ten_hang,
                'dm_sat_kg': dm_sat,
                'dm_day_kg': dm_day,
                'dm_dinh': int(dm_dinh) if dm_dinh > 0 else 0
            })
    
    return dan_items

def create_dan_item(product_code, piece_code, piece_name):
    """Create Mảnh Đan Item"""
    item_code = f"DAN-{piece_code}"
    
    if frappe.db.exists("Item", item_code):
        return item_code
    
    try:
        doc = frappe.new_doc("Item")
        doc.item_code = item_code
        doc.item_name = f"Mảnh đan {piece_name}"
        doc.item_group = "Mảnh Đan"
        doc.stock_uom = "Cái"
        doc.is_stock_item = 1
        doc.insert(ignore_permissions=True)
        return item_code
    except Exception as e:
        print(f"  Error creating {item_code}: {e}")
        return None

def find_phoi_item(piece_code):
    """Find corresponding PHOI item"""
    # Try multiple patterns
    patterns = [
        f"PHOI-{piece_code}",
        f"PHOI-{piece_code.replace('JSE ', '')}",
        f"PHOI-{piece_code.replace('IEA', 'I')}",
    ]
    
    for pattern in patterns:
        if frappe.db.exists("Item", pattern):
            return pattern
    
    return None

def create_dan_bom(dan_code, phoi_code, dm_day_kg, dm_dinh):
    """Create BOM for Mảnh Đan"""
    bom_name = f"BOM-{dan_code}-001"
    
    if frappe.db.exists("BOM", bom_name):
        return bom_name
    
    try:
        bom = frappe.new_doc("BOM")
        bom.item = dan_code
        bom.company = "Import Export Asia"
        bom.currency = "VND"
        bom.quantity = 1
        bom.is_active = 1
        bom.is_default = 1
        bom.with_operations = 0
        
        # Add Phôi sơn
        if phoi_code:
            bom.append("items", {"item_code": phoi_code, "qty": 1})
        
        # Add Dây mây
        if dm_day_kg > 0:
            if frappe.db.exists("Item", "DAY-NAU-08"):
                bom.append("items", {"item_code": "DAY-NAU-08", "qty": dm_day_kg})
        
        # Add Đinh
        if dm_dinh > 0:
            if frappe.db.exists("Item", "DINH-F10"):
                bom.append("items", {"item_code": "DINH-F10", "qty": dm_dinh})
        
        bom.insert(ignore_permissions=True)
        return bom.name
    except Exception as e:
        print(f"  Error creating BOM for {dan_code}: {e}")
        return None

def create_all():
    """Create all Mảnh Đan items and BOMs"""
    print("=== CREATING MẢNH ĐAN ITEMS AND BOMS ===\n")
    
    xl = pd.ExcelFile(DINHMUCAT_GCN_PATH)
    
    total_created = 0
    
    for sheet in xl.sheet_names[:20]:  # First 20 sheets
        product_code = SHEET_PRODUCT_MAP.get(sheet, None)
        if not product_code:
            continue
        
        print(f"\n📦 Processing {sheet} -> {product_code}")
        
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        dan_items = parse_gcn_sheet(df, sheet)
        
        for item in dan_items:
            dan_code = create_dan_item(product_code, item['ma_hang'], item['ten_hang'])
            if dan_code:
                phoi_code = find_phoi_item(item['ma_hang'])
                bom = create_dan_bom(dan_code, phoi_code, item['dm_day_kg'], item['dm_dinh'])
                if bom:
                    print(f"  ✓ {dan_code}: dây={item['dm_day_kg']}kg, đinh={item['dm_dinh']}")
                    total_created += 1
    
    frappe.db.commit()
    
    print(f"\n=== COMPLETE ===")
    print(f"Total Mảnh Đan created: {total_created}")

if __name__ == "__main__":
    create_all()
