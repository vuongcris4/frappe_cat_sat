#!/usr/bin/env python3
"""
Complete re-import of Cutting Specification details from PhoiSat files
Run: bench --site erp.dongnama.app execute cat_sat.scripts.import_phoisat.import_all
"""
import pandas as pd
import frappe
import re
import os

# Product to file mapping
PRODUCT_FILES = {
    'I1': '1. BANG THEO DOI SAT I1.xlsx',
    'I2': '2. BANG THEO DOI SAT I2.xlsx',
    'I3': '3. BANG THEO DOI SAT I3.xlsx',
    'I5': '5.2.BANG THEO DOI SAT I5.xlsx',
    'I6': '5.BANG THEO DOI SAT I6.xlsx',
    'I8': '5.4.BANG THEO DOI SAT I8.xlsx',
    'I9': '6.BANG THEO DOI SAT I9.xlsx',
    'I10': '6.BANG THEO DOI SAT I10 VIDAXL.xlsx',
    'I20': '11.BANG THEO DOI SAT I20 VIDAXL.xlsx',
    'I21': '12.BANG THEO DOI SAT I21 VIDAXL.xlsx',
    'I22': '5.1. THUNG SOT MEYING I22.xlsx',
    'I25': '5.3 BANG THEO DOI SAT I25.xlsx',
}

def parse_segments_from_excel(filepath, product_code):
    """Parse segment data from PhoiSat Excel file"""
    segments = []
    
    try:
        xl = pd.ExcelFile(filepath)
        # Try first sheet or sheet matching product code
        sheet = xl.sheet_names[0]
        for s in xl.sheet_names:
            if product_code.upper() in s.upper():
                sheet = s
                break
        
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        
        # Scan for segment patterns
        for idx, row in df.iterrows():
            for col_idx, cell in enumerate(row):
                if pd.notna(cell):
                    cell_str = str(cell).strip()
                    # Match segment codes like I9.1.1, I3.1.2
                    segment_match = re.match(rf'{product_code}\.(\d+)\.(\d+)', cell_str, re.IGNORECASE)
                    if segment_match:
                        piece_num = segment_match.group(1)
                        segment_num = segment_match.group(2)
                        
                        # Search for profile and values in surrounding columns
                        profile = None
                        length_cm = 0
                        qty = 1
                        
                        # Look in next columns
                        for i in range(1, 15):
                            if col_idx + i < len(row):
                                next_cell = row.iloc[col_idx + i]
                                if pd.notna(next_cell):
                                    next_str = str(next_cell).upper().strip()
                                    
                                    # Detect profile
                                    if profile is None and any(p in next_str for p in ['V1', 'V2', 'H1', 'H0', 'FI', 'F1']):
                                        profile = next_str
                                    
                                    # Detect cm unit
                                    if next_str == 'CM':
                                        # Next values are length and qty
                                        if col_idx + i + 1 < len(row):
                                            try:
                                                length_cm = float(row.iloc[col_idx + i + 1])
                                            except:
                                                pass
                                        if col_idx + i + 2 < len(row):
                                            try:
                                                qty = int(float(row.iloc[col_idx + i + 2]))
                                            except:
                                                qty = 1
                                        break
                        
                        if profile:
                            # Normalize profile
                            profile_clean = normalize_profile(profile)
                            
                            segments.append({
                                'piece_code': f'{product_code}.{piece_num}',
                                'piece_name': f'Mảnh {piece_num}',
                                'segment_name': cell_str,
                                'steel_profile': profile_clean,
                                'length_mm': int(length_cm * 10) if length_cm else 0,  # cm to mm
                                'qty_per_unit': qty,
                                'total_qty': qty
                            })
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    
    return segments

def normalize_profile(profile):
    """Normalize steel profile names"""
    profile = profile.upper().strip()
    
    if 'V15' in profile:
        return 'V15'
    elif 'V18' in profile:
        return 'V18'
    elif 'V20' in profile:
        return 'V20'
    elif 'V25' in profile:
        return 'V25'
    elif 'V10' in profile:
        return 'V10'
    elif 'V12' in profile:
        return 'V12'
    elif 'V14' in profile:
        return 'V14'
    elif 'H10-20' in profile or 'H10*20' in profile:
        return 'H10-20'
    elif 'H13-26' in profile or 'H13*26' in profile:
        return 'H13-26'
    elif 'H15-35' in profile or 'H15*35' in profile:
        return 'H15-35'
    elif 'FI4' in profile or 'F4' in profile:
        return 'Fi4'
    elif 'FI6' in profile or 'F6' in profile:
        return 'Fi6'
    elif 'FI8' in profile or 'F8' in profile:
        return 'Fi8'
    elif 'FI10' in profile or 'F10' in profile:
        return 'Fi10'
    elif 'FI19' in profile or 'F19' in profile:
        return 'Fi19'
    else:
        return profile.replace(' ', '-')

def update_cutting_spec(product_code, segments):
    """Update or create Cutting Specification with segments"""
    if not segments:
        print(f"  ⚠ No segments for {product_code}")
        return False
    
    # Check if spec exists
    if not frappe.db.exists("Cutting Specification", product_code):
        print(f"  ⚠ Spec {product_code} not found")
        return False
    
    # Clear existing details and add new ones via SQL
    frappe.db.sql("""
        DELETE FROM `tabCutting Detail` WHERE parent = %s
    """, product_code)
    
    # Insert new details
    for idx, seg in enumerate(segments):
        frappe.db.sql("""
            INSERT INTO `tabCutting Detail` 
            (name, parent, parenttype, parentfield, idx, 
             piece_code, piece_name, segment_name, steel_profile, 
             length_mm, qty_per_unit, total_qty, 
             punch_hole_qty, rivet_hole_qty, drill_hole_qty, bend_type)
            VALUES (%s, %s, 'Cutting Specification', 'details', %s,
                    %s, %s, %s, %s, 
                    %s, %s, %s,
                    0, 0, 0, 'Không')
        """, (
            f'{product_code}-SEG-{idx+1:03d}',
            product_code,
            idx + 1,
            seg['piece_code'],
            seg['piece_name'],
            seg['segment_name'],
            seg['steel_profile'],
            seg['length_mm'],
            seg['qty_per_unit'],
            seg['total_qty']
        ))
    
    frappe.db.commit()
    return True

def import_all():
    """Import all PhoiSat data"""
    base_path = '/workspace/frappe-bench/input_data/DinhMuc/PhoiSat'
    
    print("=== IMPORTING PHOISAT DATA ===\n")
    
    total_imported = 0
    
    for product_code, filename in PRODUCT_FILES.items():
        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath):
            print(f"✗ File not found: {filename}")
            continue
        
        print(f"Processing {product_code}...")
        segments = parse_segments_from_excel(filepath, product_code)
        
        if segments:
            if update_cutting_spec(product_code, segments):
                print(f"  ✓ {product_code}: {len(segments)} segments")
                total_imported += len(segments)
            else:
                print(f"  ⚠ {product_code}: Failed to update")
        else:
            print(f"  ⚠ {product_code}: No segments found")
    
    print(f"\n=== COMPLETE ===")
    print(f"Total segments imported: {total_imported}")

if __name__ == "__main__":
    import_all()
