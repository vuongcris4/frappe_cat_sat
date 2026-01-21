"""
Excel to ERPNext Import Script
Đọc file Excel chứa BOM (Bill of Materials) và tự động tạo:
- Items
- Cutting Specifications
- Item Groups (nếu chưa có)

Usage:
    from cat_sat.setup.import_from_excel import import_bom_excel
    import_bom_excel('/path/to/excel_file.xlsx')
"""

import frappe
import pandas as pd
from frappe.utils import cstr
import re


def read_excel_bom(file_path, sheet_name=0):
    """
    Đọc file Excel BOM
    
    Expected columns:
    - Mã SP / Product Code
    - Mã mảnh / Piece Code  
    - Tên mảnh / Piece Name
    - Loại sắt / Steel Profile (Fi21, V12, etc.)
    - Kích thước / Length (mm)
    - Số lượng / Quantity
    - Ghi chú / Note (optional)
    """
    
    print(f"Reading Excel file: {file_path}")
    
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"✅ Loaded {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"❌ Error reading Excel: {str(e)}")
        return None


def detect_columns(df):
    """
    Tự động detect cột nào là cột gì
    """
    
    columns = list(df.columns)
    mapping = {}
    
    # Detect Product Code
    for col in columns:
        col_lower = str(col).lower()
        if any(x in col_lower for x in ['mã sp', 'product code', 'ma sp', 'item code']):
            mapping['product_code'] = col
        elif any(x in col_lower for x in ['mã mảnh', 'piece code', 'ma manh', 'segment']):
            mapping['piece_code'] = col
        elif any(x in col_lower for x in ['tên mảnh', 'piece name', 'ten manh', 'piece_name']):
            mapping['piece_name'] = col
        elif any(x in col_lower for x in ['loại sắt', 'steel', 'loai sat', 'profile']):
            mapping['steel_profile'] = col
        elif any(x in col_lower for x in ['kích thước', 'length', 'kich thuoc', 'size', 'chiều dài']):
            mapping['length'] = col
        elif any(x in col_lower for x in ['số lượng', 'quantity', 'so luong', 'qty']):
            mapping['quantity'] = col
        elif any(x in col_lower for x in ['ghi chú', 'note', 'ghi chu', 'remark']):
            mapping['note'] = col
    
    print("\n📋 Column Mapping:")
    for key, val in mapping.items():
        print(f"  {key}: '{val}'")
    
    return mapping


def parse_length(length_str):
    """Parse length from various formats: 499mm, 499, 0.499m"""
    if pd.isna(length_str):
        return None
    
    length_str = str(length_str).strip().lower()
    
    # Remove commas
    length_str = length_str.replace(',', '')
    
    # Extract number
    match = re.search(r'(\d+\.?\d*)', length_str)
    if not match:
        return None
    
    value = float(match.group(1))
    
    # Convert to mm
    if 'm' in length_str and 'mm' not in length_str:
        value = value * 1000  # meters to mm
    elif value < 10:  # Likely meters
        value = value * 1000
    
    return int(value)


def group_by_product(df, col_mapping):
    """Group rows by product code"""
    
    product_col = col_mapping.get('product_code')
    if not product_col:
        print("❌ Cannot find product code column!")
        return {}
    
    grouped = {}
    
    for idx, row in df.iterrows():
        product_code = cstr(row[product_col]).strip()
        if not product_code or pd.isna(product_code):
            continue
        
        if product_code not in grouped:
            grouped[product_code] = []
        
        grouped[product_code].append({
            'piece_code': cstr(row.get(col_mapping.get('piece_code', ''), '')).strip(),
            'piece_name': cstr(row.get(col_mapping.get('piece_name', ''), '')).strip(),
            'steel_profile': cstr(row.get(col_mapping.get('steel_profile', ''), '')).strip(),
            'length_mm': parse_length(row.get(col_mapping.get('length', ''), 0)),
            'quantity': int(row.get(col_mapping.get('quantity', ''), 1)) if not pd.isna(row.get(col_mapping.get('quantity', ''), 1)) else 1,
            'note': cstr(row.get(col_mapping.get('note', ''), '')).strip()
        })
    
    return grouped


def create_cutting_specification(product_code, segments_data, dry_run=False):
    """
    Create Cutting Specification from segments data
    """
    
    spec_name = product_code
    
    # Check if exists
    if frappe.db.exists("Cutting Specification", spec_name):
        print(f"  ⏭️  Cutting Spec '{spec_name}' already exists")
        return spec_name
    
    if dry_run:
        print(f"  📝 Would create Cutting Spec: {spec_name}")
        return None
    
    # Group segments by piece
    pieces_map = {}
    for seg in segments_data:
        piece_name = seg['piece_name'] or seg['piece_code']
        if piece_name not in pieces_map:
            pieces_map[piece_name] = []
        pieces_map[piece_name].append(seg)
    
    # Create spec
    spec = frappe.new_doc("Cutting Specification")
    spec.spec_name = spec_name
    
    # Add pieces
    for piece_name, segments in pieces_map.items():
        spec.append("pieces", {
            "piece_code": segments[0]['piece_code'],
            "piece_name": piece_name,
            "piece_qty": 1  # Default 1, can be adjusted
        })
    
    # Add details (segments)
    for seg in segments_data:
        if not seg['steel_profile'] or not seg['length_mm']:
            continue
        
        piece_full_name = f"{seg['piece_code']} - {seg['piece_name']}" if seg['piece_code'] and seg['piece_name'] else (seg['piece_name'] or seg['piece_code'])
        
        spec.append("details", {
            "piece_name": piece_full_name,
            "steel_profile": seg['steel_profile'],
            "segment_name": seg['piece_code'],
            "length_mm": seg['length_mm'],
            "qty_segment_per_piece": seg['quantity'],
            "note": seg['note']
        })
    
    spec.insert(ignore_permissions=True)
    print(f"  ✅ Created Cutting Spec: {spec_name}")
    
    return spec_name


def create_item_from_spec(product_code, spec_name, dry_run=False):
    """
    Create Item linked to Cutting Specification
    """
    
    item_code = product_code
    
    # Check if exists
    if frappe.db.exists("Item", item_code):
        print(f"  ⏭️  Item '{item_code}' already exists")
        return item_code
    
    if dry_run:
        print(f"  📝 Would create Item: {item_code}")
        return None
    
    # Create item
    item = frappe.new_doc("Item")
    item.item_code = item_code
    item.item_name = product_code  # Can be customized
    item.item_group = "Thành Phẩm"  # Default group
    item.stock_uom = "Cái"
    item.cutting_specification = spec_name
    
    item.insert(ignore_permissions=True)
    print(f"  ✅ Created Item: {item_code}")
    
    return item_code


def import_bom_excel(file_path, sheet_name=0, dry_run=True):
    """
    Main import function
    
    Args:
        file_path: Path to Excel file
        sheet_name: Sheet name or index (default: 0)
        dry_run: If True, only preview without creating records
    """
    
    print("\n" + "="*80)
    print("IMPORT BOM FROM EXCEL")
    print("="*80)
    print(f"File: {file_path}")
    print(f"Mode: {'DRY RUN (Preview)' if dry_run else 'LIVE (Creating Records)'}")
    print("="*80 + "\n")
    
    # Step 1: Read Excel
    df = read_excel_bom(file_path, sheet_name)
    if df is None:
        return {"success": False, "error": "Failed to read Excel"}
    
    # Step 2: Detect columns
    col_mapping = detect_columns(df)
    if not col_mapping.get('product_code'):
        return {"success": False, "error": "Cannot detect product code column"}
    
    # Step 3: Group by product
    print("\n📦 Grouping by product...")
    grouped = group_by_product(df, col_mapping)
    print(f"Found {len(grouped)} products\n")
    
    # Step 4: Create specs and items
    created_specs = []
    created_items = []
    
    for product_code, segments in grouped.items():
        print(f"\n🔧 Processing: {product_code}")
        print(f"   Segments: {len(segments)}")
        
        # Create cutting spec
        spec_name = create_cutting_specification(product_code, segments, dry_run)
        if spec_name:
            created_specs.append(spec_name)
        
        # Create item
        if not dry_run and spec_name:
            item_code = create_item_from_spec(product_code, spec_name, dry_run)
            if item_code:
                created_items.append(item_code)
    
    if not dry_run:
        frappe.db.commit()
    
    # Summary
    print("\n" + "="*80)
    print("IMPORT COMPLETE!")
    print("="*80)
    print(f"Products processed: {len(grouped)}")
    print(f"Cutting Specs created: {len(created_specs)}")
    print(f"Items created: {len(created_items)}")
    
    if dry_run:
        print("\n⚠️  THIS WAS A DRY RUN - No records created")
        print("\nTo apply changes, run:")
        print(f"  import_bom_excel('{file_path}', dry_run=False)")
    else:
        print("\n✅ All records created successfully!")
    
    print("="*80 + "\n")
    
    return {
        "success": True,
        "products": len(grouped),
        "specs_created": len(created_specs),
        "items_created": len(created_items)
    }


def quick_import(file_path):
    """Quick import with preview first"""
    print("Step 1: Preview...")
    result = import_bom_excel(file_path, dry_run=True)
    
    if result['success']:
        print("\n" + "="*80)
        confirm = input("Preview OK. Apply changes? (yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            print("\nStep 2: Applying changes...")
            return import_bom_excel(file_path, dry_run=False)
    
    return result
