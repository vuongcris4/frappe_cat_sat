#!/usr/bin/env python3
"""
Create Multi-Level BOMs from DinhMuc Excel
Run: bench --site erp.dongnama.app execute cat_sat.scripts.create_multi_bom.create_all_boms
"""
import pandas as pd
import frappe
import re

# Sheet name to Item mapping
SHEET_ITEM_MAPPING = {
    'J15': ['J15'],
    'J48': ['J48'],
    'J49': ['J49'],
    'JSE 66': ['J66'],
    'JSE 67': ['J67'],
    'GHẾ JSE 55': ['J55.C'],
    'GHẾ JSE 55 GOPLUS': ['J55.C'],
    'IEA 1=IEA 27=IEA31': ['I1', 'I27', 'I31'],
    'IEA 2=IEA 32=IEA 36': ['I2', 'I32', 'I36'],
    'IEA3=IEA 7=IEA 24': ['I3', 'I7', 'I24'],
    'IEA 3 GOPLUS ': ['I3'],
    'IEA 4=JSE 46': ['I4', 'J46'],
    'IEA 5 XÁM =IEA 5 NÂU': ['I5'],
    'IEA 6=JSE 47': ['I6', 'J47'],
    'IEA 8': ['I8'],
    'IEA 22 THÙNG SỌT': ['I22'],
    'IEA 25': ['I25'],
    'IEA 28=IEA 33': ['I28', 'I33'],
    'IEA 29=IEA 34': ['I29', 'I34'],
    'IEA 30=IEA 35': ['I30', 'I35'],
    'IEA 9': ['I9'],
    'IEA 10 DÙNG LA TẤM': ['I10'],
    'IEA 11-12 DÙNG LA TẤM': ['I11', 'I12'],
    'IEA 13-14 DÙNG LA TẤM': ['I13', 'I14'],
    'IEA 15-16 DÙNG LA TẤM': ['I15', 'I16'],
    'IEA 17,18,19': ['I17', 'I18', 'I19'],
    'IEA 20': ['I20'],
    'IEA 21': ['I21'],
    'JSE 61 GSS': ['J61.C'],
    'JSE 61 BÀN 4 GSS': ['J61.T4'],
    'JSE 61 ĐÔN GSS': ['J61.S'],
    'IEA 39-IEA 40': ['I39', 'I40'],
    'IEA 41': ['I41'],
    'IEA 42': ['I42'],
}

# Material name normalization
def normalize_material(name):
    """Normalize material name to match existing items"""
    name = str(name).strip()
    
    # Steel profiles - normalize to short codes
    patterns = [
        (r'[Ss]ắt\s*V15.*|V15.*[zZ][eE][mM]', 'V15'),
        (r'[Ss]ắt\s*V10.*|V10.*', 'V10'),
        (r'[Ss]ắt\s*V12.*|V12.*', 'V12'),
        (r'[Ss]ắt\s*V14.*|V14.*', 'V14'),
        (r'[Ss]ắt\s*V18.*|V18.*', 'V18'),
        (r'[Ss]ắt\s*V20.*|V20.*', 'V20'),
        (r'[Ss]ắt\s*H10[\-\*]?20.*|H10[\-\*]?20.*', 'H10-20'),
        (r'[Ss]ắt\s*H13[\-\*]?26.*|H13[\-\*]?26.*', 'H13-26'),
        (r'[Ss]ắt\s*H15[\-\*]?35.*|H15[\-\*]?35.*', 'H15-35'),
        (r'[Ss]ắt\s*[Ff][iI]\s*4.*|[Ff][iI]\s*4', 'Fi4'),
        (r'[Ss]ắt\s*[Ff][iI]\s*6.*|[Ff][iI]\s*6', 'Fi6'),
        (r'[Ss]ắt\s*[Ff][iI]\s*8.*|[Ff][iI]\s*8', 'Fi8'),
        (r'[Ss]ắt\s*[Ff][iI]\s*10.*|[Ff][iI]\s*10', 'Fi10'),
        (r'[Ss]ắt\s*[Ff][iI]\s*19.*|[Ff][iI]\s*19|[Ss]ắt\s*F19', 'Fi19'),
        # Chemicals
        (r'[Ss]ơn\s*tĩnh\s*điện', 'SON-TINH-DIEN'),
        (r'[Hh]óa\s*chất', 'HOA-CHAT'),
        (r'[Gg]as', 'GAS'),
        (r'[Kk]hí\s*[Cc][Oo]2', 'KHI-CO2'),
        (r'[Dd]ây\s*[Hh]àn', 'DAY-HAN'),
        # Accessories
        (r'[Tt]án\s*rút', 'TAN-RUT'),
        (r'[Đđ]inh.*[Ff]10.*đen|[Đđ]inh\s*đen.*[Ff]10', 'DINH-F10'),
        (r'[Bb]ánh\s*đá\s*cắt', 'BANH-DA-CAT'),
        # Weaving materials
        (r'[Dd]ây\s*nâu.*08', 'DAY-NAU-08'),
        (r'[Dd]ây\s*nâu.*đóm', 'DAY-NAU-DOM'),
        (r'[Dd]ây\s*đen', 'DAY-DEN'),
        (r'[Dd]ây\s*xám', 'DAY-XAM'),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return replacement
    
    return name

def parse_bom_sheet(xl, sheet_name):
    """Parse a BOM sheet and extract materials with quantities"""
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    
    materials = []
    header_row = None
    name_col = None
    uom_col = None
    qty_col = None
    
    # Find header row
    for idx, row in df.iterrows():
        row_str = ' '.join([str(c).upper() for c in row if pd.notna(c)])
        if 'TÊN VẬT TƯ' in row_str or ('STT' in row_str and 'ĐVT' in row_str):
            header_row = idx
            for col_idx, cell in enumerate(row):
                if pd.notna(cell):
                    cell_str = str(cell).upper().strip()
                    if 'TÊN VẬT TƯ' in cell_str:
                        name_col = col_idx
                    elif cell_str == 'ĐVT':
                        uom_col = col_idx
                    elif 'ĐỊNH MỨC' in cell_str:
                        qty_col = col_idx
            break
    
    if header_row is None or name_col is None:
        return materials
    
    # Parse data rows
    for idx in range(header_row + 1, len(df)):
        row = df.iloc[idx]
        
        if name_col is not None and pd.notna(row.iloc[name_col]):
            name = str(row.iloc[name_col]).strip()
            
            if not name or 'TỔNG' in name.upper() or len(name) < 2:
                continue
            
            uom = str(row.iloc[uom_col]).strip() if uom_col and pd.notna(row.iloc[uom_col]) else 'Nos'
            qty = row.iloc[qty_col] if qty_col and pd.notna(row.iloc[qty_col]) else 0
            
            try:
                qty = float(qty) if qty else 0
            except:
                qty = 0
            
            if name and qty > 0:
                normalized = normalize_material(name)
                materials.append({
                    'original_name': name,
                    'item_code': normalized,
                    'qty': qty
                })
    
    return materials

def create_bom_for_item(item_code, materials, company='Import Export Asia'):
    """Create or update BOM for an item"""
    # Check if item exists
    if not frappe.db.exists("Item", item_code):
        print(f"  ⚠ Item {item_code} not found, skipping")
        return False
    
    # Check if BOM already exists
    existing_bom = frappe.db.get_value("BOM", {"item": item_code, "is_default": 1})
    if existing_bom:
        print(f"  ℹ BOM already exists for {item_code}: {existing_bom}")
        return False
    
    # Filter valid materials
    valid_items = []
    for mat in materials:
        if frappe.db.exists("Item", mat['item_code']):
            valid_items.append(mat)
        else:
            # Try to find by exact name
            found = frappe.db.get_value("Item", {"item_name": mat['original_name']})
            if found:
                mat['item_code'] = found
                valid_items.append(mat)
    
    if not valid_items:
        print(f"  ⚠ No valid materials for {item_code}")
        return False
    
    # Create BOM
    try:
        bom = frappe.new_doc("BOM")
        bom.item = item_code
        bom.company = company
        bom.currency = "VND"
        bom.quantity = 1
        bom.is_active = 1
        bom.is_default = 1
        bom.with_operations = 0
        
        for mat in valid_items:
            bom.append("items", {
                "item_code": mat['item_code'],
                "qty": mat['qty']
            })
        
        bom.insert(ignore_permissions=True)
        print(f"  ✓ Created BOM for {item_code} with {len(valid_items)} items")
        return True
        
    except Exception as e:
        print(f"  ✗ Error creating BOM for {item_code}: {str(e)}")
        return False

def create_all_boms():
    """Create BOMs for all products from DinhMuc"""
    excel_path = '/workspace/frappe-bench/input_data/DinhMuc/DinhMucVatTu16.1.2026.xlsx'
    xl = pd.ExcelFile(excel_path)
    
    print(f"=== Creating Multi-Level BOMs ===")
    print(f"Total sheets: {len(xl.sheet_names)}")
    print()
    
    created = 0
    skipped = 0
    errors = 0
    
    for sheet_name in xl.sheet_names:
        if sheet_name == 'KHỐI LƯỢNG TIÊU HAO VẬT TƯ SƠN':
            continue
        
        item_codes = SHEET_ITEM_MAPPING.get(sheet_name, [])
        if not item_codes:
            # Try to extract from sheet name
            match = re.search(r'(I\d+|J\d+)', sheet_name)
            if match:
                item_codes = [match.group(1)]
        
        if not item_codes:
            continue
        
        print(f"Processing: {sheet_name} -> {item_codes}")
        
        materials = parse_bom_sheet(xl, sheet_name)
        if not materials:
            print(f"  ⚠ No materials found")
            continue
        
        for item_code in item_codes:
            result = create_bom_for_item(item_code, materials)
            if result:
                created += 1
            else:
                skipped += 1
    
    frappe.db.commit()
    
    print()
    print(f"=== COMPLETE ===")
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    create_all_boms()
