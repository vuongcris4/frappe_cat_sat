"""
Script cập nhật Master Data I3 (Items và BOM)
Chạy với: bench --site erp.dongnama.app execute cat_sat.scripts.update_i3_master_data.execute
"""
import frappe

def execute():
    print("🔄 Updating I3 Master Data...")
    
    # 1. Update PHOI Items names
    phoi_updates = [
        ("PHOI-I3.1", "Phôi sơn Ghế - I3", "Phôi sơn cho bộ phận Ghế của I3"),
        ("PHOI-I3.2", "Phôi sơn Bàn - I3", "Phôi sơn cho bộ phận Bàn của I3"),
    ]
    
    for item_code, item_name, description in phoi_updates:
        if frappe.db.exists("Item", item_code):
            doc = frappe.get_doc("Item", item_code)
            doc.item_name = item_name
            doc.description = description
            doc.save()
            print(f"   ✅ Updated {item_code} → {item_name}")
        else:
            print(f"   ⚠️ Item {item_code} not found")
    
    # 2. Update MANH Items names
    manh_updates = [
        ("MANH-I3.1", "Mảnh hàn Ghế - I3", "Mảnh hàn cho bộ phận Ghế của I3 (gồm Khung tựa, Tay trái, Tay phải, Mê ngồi)"),
        ("MANH-I3.2", "Mảnh hàn Bàn - I3", "Mảnh hàn cho bộ phận Bàn của I3 (gồm Chân bàn, Hông bàn, Mặt bàn)"),
    ]
    
    for item_code, item_name, description in manh_updates:
        if frappe.db.exists("Item", item_code):
            doc = frappe.get_doc("Item", item_code)
            doc.item_name = item_name
            doc.description = description
            doc.save()
            print(f"   ✅ Updated {item_code} → {item_name}")
        else:
            print(f"   ⚠️ Item {item_code} not found")
    
    # 3. Verify DAN Items (should already be correct)
    dan_items = [
        ("DAN-IEA 3.1.1", "Mảnh đan Khung tựa"),
        ("DAN-IEA 3.1.2", "Mảnh đan Tay trái"),
        ("DAN-IEA 3.1.3", "Mảnh đan Tay Phải"),
        ("DAN-IEA 3.1.4", "Mảnh đan Mê ngồi"),
        ("DAN-IEA 3.2.1", "Mảnh đan Mặt bàn"),
        ("DAN-IEA 3.2.2", "Mảnh đan Hông bàn"),
        ("DAN-IEA 3.2.3", "Mảnh đan Chân bàn"),
    ]
    
    print("\n📋 Verifying DAN Items:")
    for item_code, expected_name in dan_items:
        if frappe.db.exists("Item", item_code):
            doc = frappe.get_doc("Item", item_code)
            status = "✅" if expected_name in doc.item_name else "⚠️"
            print(f"   {status} {item_code}: {doc.item_name}")
        else:
            print(f"   ❌ {item_code} not found")
    
    # 4. Verify BOM-I3-001
    print("\n📋 Verifying BOM-I3-001:")
    if frappe.db.exists("BOM", "BOM-I3-001"):
        bom = frappe.get_doc("BOM", "BOM-I3-001")
        print(f"   Item: {bom.item} - {bom.item_name}")
        print(f"   Total Items: {len(bom.items)}")
        for item in bom.items:
            print(f"   - {item.item_code}: {item.item_name} x{item.qty}")
    else:
        print("   ❌ BOM-I3-001 not found")
    
    frappe.db.commit()
    print("\n✅ Master Data update completed!")
