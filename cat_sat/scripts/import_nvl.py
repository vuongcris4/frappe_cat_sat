#!/usr/bin/env python3
"""
Import NVL Items from Excel to ERPNext
Run this script using: bench --site erp.dongnama.app execute cat_sat.scripts.import_nvl
Or copy the logic to bench console
"""
import pandas as pd
import frappe

# UOM mapping
UOM_MAPPING = {
    'kg': 'Kg',
    'Cái': 'Cái',
    'Bộ': 'Bộ',
    'Cuộn': 'Cuộn',
    'CUỘN': 'Cuộn',
    'Cuốn': 'Cuộn',
    'Cây': 'Cây',
    'Cây/6m': 'Cây',
    'Con': 'Con',
    'm': 'Meter',
    'MÉT': 'Meter',
    'm2': 'Square Meter',
    'm3': 'Cubic Meter',
    'Lít': 'Litre',
    'Pcs': 'Nos',
    'Chiếc': 'Nos',
    'Tấn': 'Ton',
    'Chai': 'Chai',
    'Thùng': 'Thùng',
    'Tấm': 'Tấm',
    'Bì': 'Bì',
    'Lon': 'Lon',
    'TỜ': 'Tờ',
    'nhãn': 'Nhãn',
    'Nhãn': 'Nhãn',
    'Hộp': 'Hộp',
    'CAN': 'Can',
    'Viên': 'Viên',
    'Bó': 'Bó',
    'Chuyến': 'Chuyến',
    'Thanh': 'Thanh',
    'Vỉ': 'Vỉ',
    'Xô': 'Xô',
    'ram': 'Ram',
    'Ram': 'Ram',
    'CONT': 'Cont',
    'Sợi': 'Sợi',
    'BỊCH': 'Bịch',
    'Túi': 'Túi',
    'Bình': 'Bình',
    'Lô': 'Lô',
}

def import_nvl():
    """Import NVL items from Excel"""
    # Load Excel - use workspace path (server path)
    excel_path = '/workspace/frappe-bench/input_data/Danh_sach_hang_hoa_dich_vu.xlsx'
    df = pd.read_excel(excel_path, header=2)
    nvl_df = df[df['Nhóm VTHH'] == 'NVL'].copy()
    nvl_df = nvl_df.dropna(subset=['Mã'])
    
    print(f"Total NVL rows: {len(nvl_df)}")
    
    # Get existing items
    existing = set(frappe.get_all("Item", pluck="name"))
    existing_upper = {x.upper() for x in existing}
    
    created = 0
    skipped = 0
    errors = []
    
    for idx, row in nvl_df.iterrows():
        item_code = str(row['Mã']).strip()
        
        if not item_code or len(item_code) < 2:
            continue
            
        if item_code.upper() in existing_upper:
            skipped += 1
            continue
        
        item_name = str(row['Tên']).strip() if pd.notna(row['Tên']) else item_code
        uom_raw = str(row['Đơn vị tính chính']).strip() if pd.notna(row['Đơn vị tính chính']) else 'Nos'
        uom = UOM_MAPPING.get(uom_raw, 'Nos')
        
        try:
            doc = frappe.new_doc("Item")
            doc.item_code = item_code
            doc.item_name = item_name[:140]
            doc.item_group = "Raw Material"
            doc.stock_uom = uom
            doc.is_stock_item = 1
            doc.insert(ignore_permissions=True)
            created += 1
            
            if created % 100 == 0:
                frappe.db.commit()
                print(f"Created {created} items...")
                
        except Exception as e:
            errors.append(f"{item_code}: {str(e)}")
    
    frappe.db.commit()
    
    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Created: {created}")
    print(f"Skipped (existing): {skipped}")
    print(f"Errors: {len(errors)}")
    
    if errors[:10]:
        print("\nFirst 10 errors:")
        for err in errors[:10]:
            print(f"  - {err}")

if __name__ == "__main__":
    import_nvl()
