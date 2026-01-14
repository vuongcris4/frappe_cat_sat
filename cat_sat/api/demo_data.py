import frappe
from frappe.utils import nowdate


@frappe.whitelist()
def create_demo_data():
    """
    Tạo demo data cho toàn bộ flow cắt sắt IEA
    Bao gồm: Steel Profile, Cutting Specification, Item, Product Bundle, Cutting Plan
    """
    frappe.db.begin()
    try:
        results = []
        
        # 1. Tạo Steel Profiles
        results.append(create_steel_profiles())
        
        # 2. Tạo Cutting Specification (I31.27 - Ghế góc)
        results.append(create_cutting_specification())
        
        # 3. Tạo Items thành phẩm
        results.append(create_finished_items())
        
        # 4. Tạo Product Bundle (SKU khách)
        results.append(create_product_bundles())
        
        # 5. Tạo Cutting Plan
        results.append(create_cutting_plan())
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Đã tạo demo data thành công!",
            "details": results
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Lỗi tạo demo data: {e}")
        return {
            "success": False,
            "message": f"Lỗi: {str(e)}"
        }


@frappe.whitelist()
def create_steel_profiles():
    """Tạo đầy đủ Steel Profile với bundle factors theo bảng IEA"""
    profiles = [
        # V profiles
        {"profile_code": "V10", "profile_name": "Thép V 10mm", "shape": "V", "dimension": "10", "bundle_factors": "60 64 68 72 76 80 84 88 100"},
        {"profile_code": "V12", "profile_name": "Thép V 12mm", "shape": "V", "dimension": "12", "bundle_factors": "36 39 42 45 48 56 60 64"},
        {"profile_code": "V14", "profile_name": "Thép V 14mm", "shape": "V", "dimension": "14", "bundle_factors": "27 30 33 36 39"},
        {"profile_code": "V15", "profile_name": "Thép V 15mm", "shape": "V", "dimension": "15", "bundle_factors": "27 30 33 36 39"},
        {"profile_code": "V16", "profile_name": "Thép V 16mm", "shape": "V", "dimension": "16", "bundle_factors": "27 30 33 36 39"},
        {"profile_code": "V18", "profile_name": "Thép V 18mm", "shape": "V", "dimension": "18", "bundle_factors": "60 64 68 72 76 80 84 88 100"},
        {"profile_code": "V20", "profile_name": "Thép V 20mm", "shape": "V", "dimension": "20", "bundle_factors": "14 16 18 20 24 27 30"},
        {"profile_code": "V25", "profile_name": "Thép V 25mm", "shape": "V", "dimension": "25", "bundle_factors": "12 14 16 18"},
        {"profile_code": "V30", "profile_name": "Thép V 30mm", "shape": "V", "dimension": "30", "bundle_factors": "10 12 14"},
        {"profile_code": "V40", "profile_name": "Thép V 40mm", "shape": "V", "dimension": "40", "bundle_factors": "3 4"},
        {"profile_code": "V50", "profile_name": "Thép V 50mm", "shape": "V", "dimension": "50", "bundle_factors": "3 4"},
        
        # H profiles (Hộp)
        {"profile_code": "H10-20", "profile_name": "Thép Hộp 10x20", "shape": "H", "dimension": "10x20", "bundle_factors": "28 32 36 40 45 50"},
        {"profile_code": "H13-26", "profile_name": "Thép Hộp 13x26", "shape": "H", "dimension": "13x26", "bundle_factors": "15 18 21 24 32"},
        {"profile_code": "H15-35", "profile_name": "Thép Hộp 15x35", "shape": "H", "dimension": "15x35", "bundle_factors": "12 15 18"},
        {"profile_code": "H20-40", "profile_name": "Thép Hộp 20x40", "shape": "H", "dimension": "20x40", "bundle_factors": "8 12 15 16"},
        {"profile_code": "H25-50", "profile_name": "Thép Hộp 25x50", "shape": "H", "dimension": "25x50", "bundle_factors": "14 16 18 20 24 27 30"},
        
        # FI profiles (Phi)
        {"profile_code": "FI10", "profile_name": "Thép Phi 10", "shape": "FI", "dimension": "10", "bundle_factors": "60 64 68 72 76 80 84 88 100"},
        {"profile_code": "FI16", "profile_name": "Thép Phi 16", "shape": "FI", "dimension": "16", "bundle_factors": "16 18 20 22"},
        {"profile_code": "FI19", "profile_name": "Thép Phi 19", "shape": "FI", "dimension": "19", "bundle_factors": "14 16 18 20 22"},
        {"profile_code": "FI21", "profile_name": "Thép Phi 21", "shape": "FI", "dimension": "21", "bundle_factors": "14 16 18 20"},
    ]
    
    created = []
    for p in profiles:
        if not frappe.db.exists("Steel Profile", p["profile_code"]):
            doc = frappe.new_doc("Steel Profile")
            doc.profile_code = p["profile_code"]
            doc.profile_name = p["profile_name"]
            doc.shape = p.get("shape")
            doc.dimension = p.get("dimension")
            doc.bundle_factors = p["bundle_factors"]
            doc.insert(ignore_permissions=True)
            created.append(p["profile_code"])
        else:
            # Update bundle_factors nếu đã tồn tại
            frappe.db.set_value("Steel Profile", p["profile_code"], "bundle_factors", p["bundle_factors"])
    
    return f"Steel Profiles: {', '.join(created) or 'Đã tồn tại - cập nhật bundle_factors'}"


def create_cutting_specification():
    """Tạo Cutting Specification I31.27 - Ghế góc theo mẫu user"""
    spec_name = "I31.27"
    
    if frappe.db.exists("Cutting Specification", {"spec_name": spec_name}):
        return f"Cutting Specification: {spec_name} đã tồn tại"
    
    doc = frappe.new_doc("Cutting Specification")
    doc.spec_name = spec_name
    
    # Thêm các mảnh
    pieces = [
        {"piece_code": "I31.27.1", "piece_name": "Ghế góc", "piece_qty": 1},
        {"piece_code": "I31.27.1.1", "piece_name": "Mê ngồi", "piece_qty": 1},
        {"piece_code": "I31.27.1.2", "piece_name": "Tựa góc nhỏ", "piece_qty": 1},
        {"piece_code": "I31.27.1.3", "piece_name": "Tựa góc lớn", "piece_qty": 1},
        {"piece_code": "I31.27.1.4", "piece_name": "Hông ghế", "piece_qty": 1},
        {"piece_code": "I31.27.2", "piece_name": "Ghế ghép", "piece_qty": 1},
        {"piece_code": "I31.27.2.1", "piece_name": "Mê ngồi ghép", "piece_qty": 1},
        {"piece_code": "I31.27.2.2", "piece_name": "Tựa lưng", "piece_qty": 1},
        {"piece_code": "I31.27.2.3", "piece_name": "Hông ghế*2", "piece_qty": 2},
    ]
    
    for p in pieces:
        doc.append("pieces", p)
    
    # Thêm chi tiết sắt
    details = [
        # Mê ngồi (I31.27.1.1)
        {"piece_name": "Mê ngồi", "steel_profile": "V15", "segment_name": "Thanh ngang", "length_mm": 1162.2, "qty_segment_per_piece": 1, "punch_hole_qty": 2, "rivet_hole_qty": 2},
        {"piece_name": "Mê ngồi", "steel_profile": "V15", "segment_name": "Thanh dọc", "length_mm": 2375.8, "qty_segment_per_piece": 1, "punch_hole_qty": 2, "rivet_hole_qty": 1},
        {"piece_name": "Mê ngồi", "steel_profile": "FI10", "segment_name": "Ống tròn ngắn", "length_mm": 270, "qty_segment_per_piece": 1},
        {"piece_name": "Mê ngồi", "steel_profile": "FI10", "segment_name": "Chân ghế", "length_mm": 192, "qty_segment_per_piece": 4},
        
        # Tựa góc nhỏ (I31.27.1.2)
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "V15", "segment_name": "Thanh tựa 1", "length_mm": 565, "qty_segment_per_piece": 1, "punch_hole_qty": 2, "rivet_hole_qty": 1},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "V15", "segment_name": "Thanh tựa 2", "length_mm": 1289.2, "qty_segment_per_piece": 1, "punch_hole_qty": 2, "rivet_hole_qty": 1},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "V15", "segment_name": "Thanh ngang", "length_mm": 1186.6, "qty_segment_per_piece": 1, "punch_hole_qty": 2, "rivet_hole_qty": 2},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "V15", "segment_name": "Thanh ngắn", "length_mm": 323, "qty_segment_per_piece": 1},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "V15", "segment_name": "Thanh rất ngắn", "length_mm": 46, "qty_segment_per_piece": 2},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "V10", "segment_name": "V10 dài", "length_mm": 595, "qty_segment_per_piece": 2},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "FI10", "segment_name": "Ống tròn", "length_mm": 308, "qty_segment_per_piece": 1},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "V10", "segment_name": "V10 ngắn", "length_mm": 55, "qty_segment_per_piece": 3},
        {"piece_name": "Tựa góc nhỏ", "steel_profile": "FI10", "segment_name": "Ống dài", "length_mm": 593, "qty_segment_per_piece": 1},
        
        # Tựa góc lớn (I31.27.1.3)
        {"piece_name": "Tựa góc lớn", "steel_profile": "V15", "segment_name": "Thanh dài", "length_mm": 1289.2, "qty_segment_per_piece": 2, "punch_hole_qty": 2, "bend_type": "Uốn 1 đầu"},
        {"piece_name": "Tựa góc lớn", "steel_profile": "V15", "segment_name": "Thanh vừa", "length_mm": 645, "qty_segment_per_piece": 2, "punch_hole_qty": 2, "rivet_hole_qty": 1},
        {"piece_name": "Tựa góc lớn", "steel_profile": "V15", "segment_name": "Thanh ngắn", "length_mm": 46, "qty_segment_per_piece": 2},
        {"piece_name": "Tựa góc lớn", "steel_profile": "V10", "segment_name": "V10", "length_mm": 675, "qty_segment_per_piece": 2},
        {"piece_name": "Tựa góc lớn", "steel_profile": "V10", "segment_name": "V10 ngắn", "length_mm": 55, "qty_segment_per_piece": 3},
        {"piece_name": "Tựa góc lớn", "steel_profile": "FI10", "segment_name": "Phi ngắn", "length_mm": 308, "qty_segment_per_piece": 1},
        {"piece_name": "Tựa góc lớn", "steel_profile": "FI10", "segment_name": "Phi dài", "length_mm": 593, "qty_segment_per_piece": 1},
        {"piece_name": "Tựa góc lớn", "steel_profile": "FI10", "segment_name": "Phi 6", "length_mm": 37, "qty_segment_per_piece": 1},
        
        # Hông ghế (I31.27.1.4)
        {"piece_name": "Hông ghế", "steel_profile": "V15", "segment_name": "Thanh hông dài", "length_mm": 1699.8, "qty_segment_per_piece": 1, "punch_hole_qty": 1, "rivet_hole_qty": 1, "note": "2 dập"},
        {"piece_name": "Hông ghế", "steel_profile": "FI10", "segment_name": "Ống hông", "length_mm": 248, "qty_segment_per_piece": 1},
        
        # Mê ngồi ghép (I31.27.2.1)
        {"piece_name": "Mê ngồi ghép", "steel_profile": "V15", "segment_name": "Thanh dài", "length_mm": 2375.8, "qty_segment_per_piece": 1, "punch_hole_qty": 1, "rivet_hole_qty": 2},
        {"piece_name": "Mê ngồi ghép", "steel_profile": "V15", "segment_name": "Thanh vừa", "length_mm": 1162.2, "qty_segment_per_piece": 1, "punch_hole_qty": 2, "rivet_hole_qty": 2},
        {"piece_name": "Mê ngồi ghép", "steel_profile": "FI10", "segment_name": "Chân", "length_mm": 270, "qty_segment_per_piece": 1},
        {"piece_name": "Mê ngồi ghép", "steel_profile": "FI10", "segment_name": "Chân nhỏ", "length_mm": 192, "qty_segment_per_piece": 4},
        
        # Tựa lưng (I31.27.2.2)
        {"piece_name": "Tựa lưng", "steel_profile": "V15", "segment_name": "Thanh tựa dài", "length_mm": 1289.2, "qty_segment_per_piece": 2, "bend_type": "Uốn 1 đầu"},
        {"piece_name": "Tựa lưng", "steel_profile": "V15", "segment_name": "Thanh tựa vừa", "length_mm": 565, "qty_segment_per_piece": 2, "rivet_hole_qty": 1},
        {"piece_name": "Tựa lưng", "steel_profile": "V15", "segment_name": "Thanh ngắn", "length_mm": 46, "qty_segment_per_piece": 2},
        {"piece_name": "Tựa lưng", "steel_profile": "V10", "segment_name": "V10", "length_mm": 595, "qty_segment_per_piece": 1},
        {"piece_name": "Tựa lưng", "steel_profile": "FI10", "segment_name": "Phi", "length_mm": 593, "qty_segment_per_piece": 1},
        {"piece_name": "Tựa lưng", "steel_profile": "FI10", "segment_name": "Phi ngắn", "length_mm": 308, "qty_segment_per_piece": 1},
        {"piece_name": "Tựa lưng", "steel_profile": "V10", "segment_name": "V10 ngắn", "length_mm": 55, "qty_segment_per_piece": 3},
        
        # Hông ghế*2 (I31.27.2.3)
        {"piece_name": "Hông ghế*2", "steel_profile": "V15", "segment_name": "Thanh hông", "length_mm": 1699.8, "qty_segment_per_piece": 2, "punch_hole_qty": 2, "rivet_hole_qty": 2},
        {"piece_name": "Hông ghế*2", "steel_profile": "FI10", "segment_name": "Ống hông", "length_mm": 248, "qty_segment_per_piece": 2},
    ]
    
    for d in details:
        d.setdefault("punch_hole_qty", 0)
        d.setdefault("rivet_hole_qty", 0)
        d.setdefault("bend_type", "Không")
        d.setdefault("note", "")
        doc.append("details", d)
    
    doc.insert(ignore_permissions=True)
    
    return f"Cutting Specification: {doc.name} ({spec_name})"


def create_finished_items():
    """Tạo Item thành phẩm: I31.27-DEN-BE, I31.27-NAU-DO"""
    
    # Lấy Cutting Specification
    cs_name = frappe.db.get_value("Cutting Specification", {"spec_name": "I31.27"})
    
    items = [
        {
            "item_code": "I31.27-DEN-BE",
            "item_name": "Bộ ghế góc I31.27 - Dây đen, Nệm be",
            "factory_code": "I31.27",
            "wire_color": "Đen",
            "cushion_color": "Be",
            "cutting_specification": cs_name
        },
        {
            "item_code": "I31.27-NAU-DO",
            "item_name": "Bộ ghế góc I31.27 - Dây nâu, Nệm đỏ",
            "factory_code": "I31.27",
            "wire_color": "Nâu",
            "cushion_color": "Đỏ",
            "cutting_specification": cs_name
        },
    ]
    
    # Đảm bảo Item Group tồn tại
    if not frappe.db.exists("Item Group", "Thành phẩm"):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": "Thành phẩm",
            "parent_item_group": "All Item Groups"
        }).insert(ignore_permissions=True)
    
    created = []
    for item_data in items:
        if not frappe.db.exists("Item", item_data["item_code"]):
            doc = frappe.new_doc("Item")
            doc.item_code = item_data["item_code"]
            doc.item_name = item_data["item_name"]
            doc.item_group = "Thành phẩm"
            doc.stock_uom = "Cái"
            doc.is_stock_item = 1
            doc.factory_code = item_data["factory_code"]
            doc.wire_color = item_data["wire_color"]
            doc.cushion_color = item_data["cushion_color"]
            doc.cutting_specification = item_data["cutting_specification"]
            doc.insert(ignore_permissions=True)
            created.append(item_data["item_code"])
    
    return f"Items: {', '.join(created) or 'Đã tồn tại'}"


def create_product_bundles():
    """Tạo Product Bundle: VDX-SET-001 (SKU Vidaxl)"""
    bundle_code = "VDX-SET-001"
    
    if frappe.db.exists("Product Bundle", bundle_code):
        return f"Product Bundle: {bundle_code} đã tồn tại"
    
    # Tạo Item mới cho bundle 
    if not frappe.db.exists("Item", bundle_code):
        doc = frappe.new_doc("Item")
        doc.item_code = bundle_code
        doc.item_name = "Vidaxl Set 001 - Bộ ghế góc"
        doc.item_group = "Thành phẩm"
        doc.stock_uom = "Bộ"
        doc.is_stock_item = 0
        doc.insert(ignore_permissions=True)
    
    # Tạo Product Bundle
    pb = frappe.new_doc("Product Bundle")
    pb.new_item_code = bundle_code
    pb.iea_customer = None  # Có thể link tới Customer nếu đã tạo
    pb.customer_sku = "VDX-GARDEN-SET-001"
    
    # Thêm items
    pb.append("items", {
        "item_code": "I31.27-DEN-BE",
        "qty": 1,
        "description": "Ghế góc màu đen"
    })
    pb.append("items", {
        "item_code": "I31.27-NAU-DO",
        "qty": 2,
        "description": "Ghế ghép màu nâu"
    })
    
    pb.insert(ignore_permissions=True)
    
    return f"Product Bundle: {pb.name}"


def create_cutting_plan():
    """Tạo Cutting Plan với demo items"""
    plan = frappe.new_doc("Cutting Plan")
    plan.plan_date = nowdate()
    plan.status = "Draft"
    
    # Thêm items
    if frappe.db.exists("Item", "I31.27-DEN-BE"):
        plan.append("items", {
            "item_code": "I31.27-DEN-BE",
            "product_qty": 5
        })
    
    if frappe.db.exists("Item", "I31.27-NAU-DO"):
        plan.append("items", {
            "item_code": "I31.27-NAU-DO",
            "product_qty": 10
        })
    
    plan.insert(ignore_permissions=True)
    
    return f"Cutting Plan: {plan.name}"


@frappe.whitelist()
def clear_demo_data():
    """Xóa demo data (cẩn thận!)"""
    frappe.only_for("System Manager")
    
    # Xóa Cutting Plan
    for name in frappe.get_all("Cutting Plan", pluck="name"):
        frappe.delete_doc("Cutting Plan", name, force=True)
    
    # Xóa Product Bundle
    for name in ["VDX-SET-001"]:
        if frappe.db.exists("Product Bundle", name):
            frappe.delete_doc("Product Bundle", name, force=True)
    
    # Xóa Items
    for code in ["I31.27-DEN-BE", "I31.27-NAU-DO", "VDX-SET-001"]:
        if frappe.db.exists("Item", code):
            frappe.delete_doc("Item", code, force=True)
    
    # Xóa Cutting Specification
    for name in frappe.get_all("Cutting Specification", {"spec_name": "I31.27"}, pluck="name"):
        frappe.delete_doc("Cutting Specification", name, force=True)
    
    frappe.db.commit()
    return "Đã xóa demo data"
